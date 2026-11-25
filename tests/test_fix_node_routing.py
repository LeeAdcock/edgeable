import inspect
import os
import shutil
import sys
import tempfile
import unittest

from edgeable import GraphDatabase, GraphNode


class _DbTestCase(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.mkdtemp(prefix="edgeable-test-")
        self.addCleanup(shutil.rmtree, self._dir, True)
        self.db = GraphDatabase(filename=os.path.join(self._dir, "graph.db"))

    def nodes(self, ids):
        return [self.db.put_node(id) for id in ids]

    def chain(self, length):
        """Build a chain of nodes directly, to keep the test fast."""
        nodes = self.nodes(range(length))
        for previous, node in zip(nodes, nodes[1:]):
            previous.attach(node, directed=True)
        return nodes


class TestFindRoute(_DbTestCase):
    """Issue #10"""

    def test_long_route(self):
        length = 100001
        nodes = self.chain(length)
        self.assertGreater(length, sys.getrecursionlimit())

        route = nodes[0].find_route_to(nodes[-1])

        self.assertEqual(len(route), length)
        self.assertEqual([n.get_id() for n in route], list(range(length)))
        self.assertIsNone(nodes[-1].find_route_to(nodes[0]))

    def test_long_route_alternatives(self):
        nodes = self.chain(3000)
        routes = nodes[0].find_routes_to(nodes[-1], effort=1)
        self.assertEqual(len(routes), 1)
        self.assertEqual(len(routes[0]), 3000)

    def test_route_to_self(self):
        A, B = self.nodes("AB")
        A.attach(B)
        self.assertEqual(A.find_route_to(A), [A])
        self.assertEqual(A.find_routes_to(A), [[A]])

    def test_no_route(self):
        A, B, C = self.nodes("ABC")
        A.attach(B)
        self.assertIsNone(A.find_route_to(C))
        self.assertEqual(A.find_routes_to(C), [])

    def test_route_is_list_of_graph_nodes(self):
        A, B, C = self.nodes("ABC")
        A.attach(B)
        B.attach(C)

        route = A.find_route_to(C)

        self.assertIsInstance(route, list)
        self.assertEqual(route, [A, B, C])
        for expected, actual in zip([A, B, C], route):
            self.assertIs(type(actual), GraphNode)
            self.assertIs(actual, expected)

    def test_route_is_shortest(self):
        A, B, C, D, E = self.nodes("ABCDE")
        A.attach(B)
        B.attach(C)
        C.attach(D)
        D.attach(E)
        A.attach(D)
        self.assertEqual(A.find_route_to(E), [A, D, E])

    def test_skip(self):
        A, B, C, D = self.nodes("ABCD")
        A.attach(B)
        A.attach(C)
        B.attach(D)
        C.attach(D)

        self.assertEqual(A.find_route_to(D), [A, B, D])
        self.assertEqual(A.find_route_to(D, [B]), [A, C, D])
        self.assertEqual(A.find_route_to(D, skip={B}), [A, C, D])
        self.assertEqual(A.find_route_to(D, (node for node in [B])), [A, C, D])
        self.assertIsNone(A.find_route_to(D, [B, C]))
        self.assertIsNone(A.find_route_to(D, [D]))

    def test_skip_default_is_not_shared(self):
        default = inspect.signature(GraphNode.find_route_to).parameters["skip"].default
        self.assertIsNone(default)

    def test_skip_argument_is_not_modified(self):
        A, B, C = self.nodes("ABC")
        A.attach(B)
        B.attach(C)
        skip = []
        A.find_route_to(C, skip)
        A.find_routes_to(C)
        self.assertEqual(skip, [])

    def test_find_route_validates_destination(self):
        (A,) = self.nodes("A")
        with self.assertRaises(RuntimeError):
            A.find_route_to("B")
        with self.assertRaises(RuntimeError):
            A.find_routes_to("B")

    def test_routes(self):
        A, B, C, D, E = self.nodes("ABCDE")
        A.attach(B)
        A.attach(C)
        B.attach(D)
        C.attach(D)
        D.attach(E)

        self.assertEqual(A.find_routes_to(E), [[A, B, D, E], [A, C, D, E]])
        self.assertEqual(A.find_routes_to(E, effort=0), [[A, B, D, E]])

    def test_routes_only_avoid_intermediate_nodes(self):
        # the ends of the route are never skipped, so a direct route has
        # no alternatives
        A, B, C = self.nodes("ABC")
        A.attach(B)
        B.attach(C)
        A.attach(C)

        self.assertEqual(A.find_routes_to(C), [[A, C]])
        self.assertEqual(A.find_routes_to(B), [[A, B]])

    def test_routes_match_exhaustive_search(self):
        # a ladder, where the order in which nodes are skipped used to
        # cause the same search to be repeated
        nodes = self.nodes(range(8))
        for a, b in [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (3, 5), (4, 6)]:
            nodes[a].attach(nodes[b])
        nodes[5].attach(nodes[6])
        nodes[1].attach(nodes[4])
        nodes[6].attach(nodes[7])

        ids = [[n.get_id() for n in r] for r in nodes[0].find_routes_to(nodes[7])]

        self.assertEqual(
            ids,
            [
                [0, 1, 4, 6, 7],
                [0, 2, 3, 4, 6, 7],
                [0, 1, 3, 5, 6, 7],
                [0, 2, 3, 5, 6, 7],
            ],
        )

    def test_routes_on_dense_graph(self):
        # every skip combination was searched before, in every order
        nodes = self.nodes(range(9))
        for a in nodes:
            for b in nodes:
                a.attach(b)
        nodes[0].detach(nodes[-1])

        routes = nodes[0].find_routes_to(nodes[-1], effort=7)

        self.assertEqual(len(routes), 7)
        for route in routes:
            self.assertEqual(len(route), 3)

    def test_dangling_edges_are_skipped(self):
        A, B, C, D = self.nodes("ABCD")
        A.attach(B)
        A.attach(C)
        B.attach(D)
        C.attach(D)
        # a dangling edge, as could be loaded from a file written by an
        # older version
        del self.db._graph["B"]

        self.assertEqual(A.find_route_to(D), [A, C, D])
        self.assertIsNone(A.find_route_to(B))
        self.assertEqual(A.find_routes_to(D), [[A, C, D]])
        self.assertEqual(A.find_neighbors(5), [C, D])


class TestFindNeighbors(_DbTestCase):
    """Issue #10"""

    @staticmethod
    def weight(edge):
        return edge.get_property("w")

    def test_weighted_neighbors(self):
        A, B, C, D = self.nodes("ABCD")
        A.attach(B, {"w": 3})
        A.attach(C, {"w": 1})
        C.attach(B, {"w": 1})
        B.attach(D, {"w": 1})

        self.assertEqual(A.find_neighbors(3, self.weight), [C, B, D])
        self.assertEqual(A.find_neighbors(2, self.weight), [C, B])
        self.assertEqual(A.find_neighbors(1, self.weight), [C])
        self.assertEqual(A.find_neighbors(0.5, self.weight), [])

    def test_unit_distance_order_is_breadth_first(self):
        A, B, C, D, E, F = self.nodes("ABCDEF")
        A.attach(C)
        A.attach(B)
        C.attach(F)
        B.attach(E)
        B.attach(D)
        E.attach(F)

        self.assertEqual(A.find_neighbors(1), [C, B])
        self.assertEqual(A.find_neighbors(2), [C, B, F, E, D])
        self.assertEqual(A.find_neighbors(10), [C, B, F, E, D])
        self.assertEqual(A.find_neighbors(0), [])

    def test_directed_edges(self):
        A, B, C = self.nodes("ABC")
        A.attach(B, directed=True)
        C.attach(A, directed=True)

        self.assertEqual(A.find_neighbors(5), [B])

    def test_zero_and_fractional_distances(self):
        A, B, C = self.nodes("ABC")
        A.attach(B, {"w": 0})
        B.attach(C, {"w": 0.5})

        self.assertEqual(A.find_neighbors(0, self.weight), [B])
        self.assertEqual(A.find_neighbors(0.5, self.weight), [B, C])

    def test_negative_distance_raises(self):
        A, B = self.nodes("AB")
        A.attach(B, {"w": -1})

        with self.assertRaises(RuntimeError):
            A.find_neighbors(3, self.weight)

    def test_non_numeric_distance_raises(self):
        A, B = self.nodes("AB")
        A.attach(B)

        with self.assertRaises(RuntimeError):
            A.find_neighbors(3, self.weight)
        with self.assertRaises(RuntimeError):
            A.find_neighbors(3, lambda edge: float("nan"))

    def test_neighbors_of_long_chain(self):
        nodes = self.chain(5000)
        self.assertEqual(nodes[0].find_neighbors(10000), nodes[1:])
