import unittest
from edgeable import GraphDatabase


class TestNode(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_add_node(self):
        self.db.get_node("A")
        self.assertEqual(self.db.get_node_count(), 1)

    def test_node_get_set_property(self):
        A = self.db.get_node("A")
        A.set_property("my_key", "my_value")

        self.assertEqual(A.get_property("my_key"), "my_value")

    def test_node_get_properties(self):
        A = self.db.get_node("A")
        A.set_property("my_key", "my_value")

        properties = A.get_properties()
        self.assertEqual(properties, {"my_key": "my_value"})

    def test_node_properties_returns_copy(self):
        A = self.db.get_node("A")
        A.set_property("my_key", "my_value")

        properties = A.get_properties()
        properties["my_key_2"] = "my_value_2"
        self.assertEqual(A.get_properties(), {"my_key": "my_value"})

    def test_attach_node(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B)
        self.assertEqual(len(A.get_edges()), 1)
        self.assertEqual(len(B.get_edges()), 1)

        self.assertEqual(A.get_edges()[0].get_destination().get_id(), B.get_id())
        self.assertEqual(B.get_edges()[0].get_destination().get_id(), A.get_id())

    def test_attach_node_directed(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B, directed=True)
        self.assertEqual(len(A.get_edges()), 1)
        self.assertEqual(len(B.get_edges()), 0)

        self.assertEqual(A.get_edges()[0].get_destination().get_id(), B.get_id())

    def test_get_edges(self):
        A = self.db.get_node("A")

        B = self.db.get_node("B")
        B.attach(A)

        C = self.db.get_node("C")
        C.attach(A)

        self.assertEqual(len(A.get_edges()), 2)
        self.assertEqual(
            len(A.get_edges(lambda edge: edge.destination.get_id() == "B")), 1
        )

    def test_attach_node_overwrite_properties(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B, {"my_key": "my_value"})
        A.attach(B, {"my_key_2": "my_value_2"})

        self.assertEqual(
            A.get_edges()[0].get_properties(),
            {"my_key": "my_value", "my_key_2": "my_value_2"},
        )

    def test_get_edge(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B)

        self.assertEqual(A.get_edge(B).get_destination(), B)
        self.assertEqual(A.get_edge(B).get_source(), A)

        self.assertEqual(B.get_edge(A).get_destination(), A)
        self.assertEqual(A.get_edge(B).get_source(), A)

    def test_attach_node_with_properties(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B, {"my_key": "my_value"})
        self.assertEqual(A.get_edges()[0].get_property("my_key"), "my_value")
        self.assertEqual(B.get_edges()[0].get_property("my_key"), "my_value")

    def test_detach_node(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B)

        self.db.get_node("B").detach()
        self.assertEqual(len(A.get_edges()), 0)
        self.assertEqual(len(B.get_edges()), 0)
        self.assertEqual(self.db.get_node_count(), 2)

    def test_detach_node_directed(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B)

        self.db.get_node("B").detach(directed=True)
        self.assertEqual(len(A.get_edges()), 1)
        self.assertEqual(len(B.get_edges()), 0)
        self.assertEqual(self.db.get_node_count(), 2)

    def test_delete_node(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B)

        A.delete()

        self.assertEqual(self.db.get_node_count(), 1)
        self.assertEqual(len(B.get_edges()), 0)

    def test_node_route(self):
        A = self.db.get_node("A")

        B = self.db.get_node("B")
        B.attach(A)

        C = self.db.get_node("C")
        C.attach(B)

        D = self.db.get_node("D")
        D.attach(C)

        self.assertEqual(A.find_route_to(B), [A, B])
        self.assertEqual(A.find_route_to(C), [A, B, C])

        self.assertEqual(C.find_route_to(A), [C, B, A])
        self.assertEqual(B.find_route_to(A), [B, A])

    def test_node_route_circular(self):
        A = self.db.get_node("A")

        B = self.db.get_node("B")
        B.attach(A)

        C = self.db.get_node("C")
        C.attach(B)

        D = self.db.get_node("D")
        D.attach(C)
        D.attach(A)

        self.assertEqual(A.find_route_to(D), [A, D])
        self.assertEqual(D.find_route_to(A), [D, A])

    def test_node_route_directed(self):
        A = self.db.get_node("A")

        B = self.db.get_node("B")
        B.attach(A, directed=True)

        C = self.db.get_node("C")
        C.attach(B, directed=True)

        D = self.db.get_node("D")
        D.attach(C, directed=True)
        A.attach(D, directed=True)

        self.assertEqual(A.find_route_to(D), [A, D])
        self.assertEqual(D.find_route_to(A), [D, C, B, A])