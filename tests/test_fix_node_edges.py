import functools
import os
import shutil
import tempfile
import unittest

from edgeable import GraphDatabase


class _DbTestCase(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.mkdtemp(prefix="edgeable-test-")
        self.addCleanup(shutil.rmtree, self._dir, True)
        self.db = self.new_db("graph.db")

    def new_db(self, name):
        return GraphDatabase(filename=os.path.join(self._dir, name))

    def nodes(self, ids):
        return [self.db.put_node(id) for id in ids]


class TestDetachAndDelete(_DbTestCase):
    """Issue #2"""

    def test_detach_all_removes_every_edge(self):
        A, B, C, D = self.nodes("ABCD")
        A.attach(B)
        A.attach(C)
        A.attach(D)

        self.assertTrue(A.detach())

        self.assertEqual(A.get_edges(), [])
        self.assertEqual(self.db.get_edge_count(), 0)

    def test_detach_all_directed_keeps_reverse_edges(self):
        A, B, C = self.nodes("ABC")
        A.attach(B)
        A.attach(C)

        self.assertTrue(A.detach(directed=True))

        self.assertEqual(A.get_edges(), [])
        self.assertTrue(B.has_edge(A))
        self.assertTrue(C.has_edge(A))

    def test_detach_all_without_edges(self):
        (A,) = self.nodes("A")
        self.assertFalse(A.detach())

    def test_delete_removes_all_reverse_edges(self):
        A, B, C, D = self.nodes("ABCD")
        A.attach(B)
        A.attach(C)
        A.attach(D)
        B.attach(C)

        self.assertTrue(A.delete())

        self.assertEqual(self.db.get_nodes(), [B, C, D])
        self.assertEqual(self.db.get_edge_count(), 2)
        for node in (B, C, D):
            self.assertNotIn("A", node._edges)

    def test_delete_removes_incoming_directed_edges(self):
        A, B = self.nodes("AB")
        B.attach(A, directed=True)

        A.delete()

        self.assertEqual(B.get_edges(), [])
        self.assertEqual(B.find_neighbors(), [])
        self.assertEqual(self.db.get_edge_count(), 0)

    def test_delete_node_veto_keeps_node_and_edges(self):
        A, B, C = self.nodes("ABC")
        A.attach(B)
        C.attach(A, directed=True)
        deleted_edges = []
        self.db.on_delete_edge(deleted_edges.append)
        self.db.on_delete_node(lambda node: False)

        self.assertFalse(A.delete())

        self.assertTrue(self.db.has_node("A"))
        self.assertEqual(self.db.get_edge_count(), 3)
        self.assertEqual(deleted_edges, [])

    def test_delete_notifies_edge_callbacks_which_cannot_cancel(self):
        A, B, C = self.nodes("ABC")
        A.attach(B)
        C.attach(A, directed=True)
        deleted_edges = []

        def callback(edge):
            deleted_edges.append(str(edge))
            return False

        self.db.on_delete_edge(callback)

        self.assertTrue(A.delete())

        self.assertEqual(sorted(deleted_edges), ["A->B", "B->A", "C->A"])
        self.assertFalse(self.db.has_node("A"))
        self.assertEqual(self.db.get_edge_count(), 0)

    def test_delete_when_edge_callback_attaches_new_edges(self):
        A, B, C = self.nodes("ABC")
        A.attach(B)
        self.db.on_delete_edge(lambda edge: edge.get_source().attach(C))

        A.delete()

        self.assertFalse(self.db.has_node("A"))
        for node in self.db.get_nodes():
            self.assertNotIn("A", node._edges)

    def test_all_delete_node_callbacks_run_after_cancel(self):
        (A,) = self.nodes("A")
        calls = []
        self.db.on_delete_node(lambda node: False)
        self.db.on_delete_node(calls.append)

        A.delete()

        self.assertEqual(calls, [A])

    def test_deleted_node_cannot_be_used(self):
        A, B = self.nodes("AB")
        A.delete()

        with self.assertRaises(RuntimeError):
            A.delete()
        with self.assertRaises(RuntimeError):
            A.attach(B)
        with self.assertRaises(RuntimeError):
            A.detach()

    def test_stale_handle_cannot_delete_replacement_node(self):
        (A,) = self.nodes("A")
        A.delete()
        A2 = self.db.put_node("A")

        with self.assertRaises(RuntimeError):
            A.delete()
        self.assertIs(self.db.get_node("A"), A2)


class TestAttachDetach(_DbTestCase):
    """Issue #7"""

    def test_reattach_mirrors_properties(self):
        A, B = self.nodes("AB")
        self.assertTrue(A.attach(B, {"w": 1}))
        self.assertFalse(A.attach(B, {"w": 2, "x": 3}))

        self.assertEqual(A.get_edge(B).get_properties(), {"w": 2, "x": 3})
        self.assertEqual(B.get_edge(A).get_properties(), {"w": 2, "x": 3})

    def test_reattach_directed_does_not_mirror_properties(self):
        A, B = self.nodes("AB")
        A.attach(B, {"w": 1})
        A.attach(B, {"w": 2}, directed=True)

        self.assertEqual(A.get_edge(B).get_properties(), {"w": 2})
        self.assertEqual(B.get_edge(A).get_properties(), {"w": 1})

    def test_undirected_attach_over_directed_edge_creates_reverse(self):
        A, C = self.nodes("AC")
        A.attach(C, {"w": 1}, directed=True)

        self.assertTrue(A.attach(C, {"x": 2}))

        self.assertTrue(C.has_edge(A))
        self.assertEqual(C.get_edge(A).get_properties(), {"x": 2})
        self.assertEqual(A.get_edge(C).get_properties(), {"w": 1, "x": 2})

    def test_edges_do_not_share_property_dicts(self):
        A, B = self.nodes("AB")
        properties = {"w": 1}
        A.attach(B, properties)
        A.get_edge(B).set_property("w", 2, directed=True)

        self.assertEqual(B.get_edge(A).get_property("w"), 1)
        self.assertEqual(properties, {"w": 1})

    def test_attach_to_self(self):
        (A,) = self.nodes("A")
        self.assertFalse(A.attach(A))
        self.assertEqual(A.get_edges(), [])

    def test_attach_cancelled_in_one_direction_creates_nothing(self):
        D, E = self.nodes("DE")
        self.db.on_create_edge(lambda edge: edge.get_source().get_id() != "E")

        self.assertFalse(D.attach(E))

        self.assertFalse(D.has_edge(E))
        self.assertFalse(E.has_edge(D))

        # the direction which is not vetoed can still be created on its own
        self.assertTrue(D.attach(E, directed=True))
        self.assertTrue(D.has_edge(E))

    def test_attach_cancelled_leaves_existing_edge_untouched(self):
        A, B = self.nodes("AB")
        A.attach(B, {"w": 1}, directed=True)
        self.db.on_create_edge(lambda edge: False)

        self.assertFalse(A.attach(B, {"w": 2}))

        self.assertEqual(A.get_edge(B).get_properties(), {"w": 1})
        self.assertFalse(B.has_edge(A))

    def test_attach_returns_false_when_cancelled(self):
        A, D = self.nodes("AD")
        self.db.on_create_edge(lambda edge: False)

        self.assertFalse(D.attach(A))
        self.assertEqual(self.db.get_edge_count(), 0)

    def test_all_create_edge_callbacks_run_after_cancel(self):
        A, B = self.nodes("AB")
        calls = []
        self.db.on_create_edge(lambda edge: False)
        self.db.on_create_edge(lambda edge: calls.append(str(edge)))

        A.attach(B)

        self.assertEqual(calls, ["A->B", "B->A"])

    def test_only_false_cancels(self):
        A, B = self.nodes("AB")
        self.db.on_create_edge(lambda edge: 0)
        self.db.on_delete_edge(lambda edge: None)

        self.assertTrue(A.attach(B))
        self.assertTrue(A.detach(B))

    def test_create_edge_callback_properties_are_kept(self):
        A, B = self.nodes("AB")
        self.db.on_create_edge(lambda edge: edge.set_property("seen", True))

        A.attach(B, {"w": 1})

        self.assertEqual(A.get_edge(B).get_properties(), {"w": 1, "seen": True})
        self.assertEqual(B.get_edge(A).get_properties(), {"w": 1, "seen": True})

    def test_detach_returns_false_when_cancelled(self):
        A, B = self.nodes("AB")
        A.attach(B)
        self.db.on_delete_edge(lambda edge: False)

        self.assertFalse(A.detach(B))
        self.assertFalse(A.detach())
        self.assertFalse(A.get_edge(B).delete())

        self.assertTrue(A.has_edge(B))
        self.assertTrue(B.has_edge(A))

    def test_detach_cancelled_in_one_direction_removes_nothing(self):
        A, B = self.nodes("AB")
        A.attach(B)
        self.db.on_delete_edge(lambda edge: edge.get_source().get_id() != "B")

        self.assertFalse(A.detach(B))

        self.assertTrue(A.has_edge(B))
        self.assertTrue(B.has_edge(A))

        # the direction which is not vetoed can still be removed on its own
        self.assertTrue(A.detach(B, directed=True))
        self.assertFalse(A.has_edge(B))
        self.assertTrue(B.has_edge(A))

    def test_detach_returns_true_when_removed(self):
        A, B = self.nodes("AB")
        A.attach(B)

        self.assertTrue(A.detach(B))
        self.assertFalse(A.detach(B))
        self.assertEqual(self.db.get_edge_count(), 0)

    def test_undirected_detach_removes_incoming_directed_edge(self):
        A, B = self.nodes("AB")
        B.attach(A, directed=True)

        self.assertTrue(A.detach(B))
        self.assertFalse(B.has_edge(A))

    def test_edge_delete_returns_whether_removed(self):
        A, B = self.nodes("AB")
        A.attach(B)
        edge = A.get_edge(B)

        self.assertTrue(edge.delete())
        self.assertFalse(edge.delete())

    def test_attach_to_node_of_other_database(self):
        (A,) = self.nodes("A")
        X = self.new_db("other.db").put_node("X")

        for directed in (True, False):
            with self.assertRaises(RuntimeError):
                A.attach(X, directed=directed)
        self.assertEqual(A.get_edges(), [])
        self.assertEqual(X._edges, {})

    def test_attach_to_same_id_in_other_database(self):
        A, B = self.nodes("AB")
        other_B = self.new_db("other.db").put_node("B")

        with self.assertRaises(RuntimeError):
            A.attach(other_B)
        self.assertEqual(A.get_edges(), [])
        self.assertEqual(B.get_edges(), [])
        self.assertEqual(other_B._edges, {})

    def test_attach_to_deleted_node(self):
        A, B = self.nodes("AB")
        B.delete()

        with self.assertRaises(RuntimeError):
            A.attach(B)
        with self.assertRaises(RuntimeError):
            A.attach(B, directed=True)
        self.assertEqual(A.get_edges(), [])

    def test_attach_validates_arguments(self):
        A, B = self.nodes("AB")
        with self.assertRaises(RuntimeError):
            A.attach("B")
        with self.assertRaises(RuntimeError):
            A.attach(B, ["w"])
        with self.assertRaises(RuntimeError):
            A.attach(B, {1: "w"})
        self.assertEqual(self.db.get_edge_count(), 0)


class TestNumericIds(_DbTestCase):
    """Issue #9"""

    def test_str_and_repr_of_numeric_node(self):
        a = self.db.put_node(1)
        self.assertEqual(str(a), "1")
        self.assertEqual(repr(a), "1")
        self.assertEqual(f"{a}", "1")
        self.assertEqual(str([a]), "[1]")

    def test_str_and_repr_of_numeric_edge(self):
        a, b = self.nodes([1, 2])
        a.attach(b)
        self.assertEqual(str(a.get_edge(b)), "1->2")
        self.assertEqual(repr(a.get_edges()), "[1->2]")

    def test_str_of_mixed_id_edge(self):
        a, b = self.nodes([1, "B"])
        a.attach(b)
        self.assertEqual(str(a.get_edge(b)), "1->B")
        self.assertEqual(str(b.get_edge(a)), "B->1")

    def test_edge_is_hashable(self):
        A, B = self.nodes("AB")
        A.attach(B)

        edges = {A.get_edge(B), A.get_edges()[0], B.get_edge(A)}

        self.assertEqual(len(edges), 2)
        self.assertEqual(hash(A.get_edge(B)), hash(A.get_edges()[0]))
        self.assertIn(A.get_edge(B), {A.get_edge(B): 1})


class TestValidation(_DbTestCase):
    """Issue #11"""

    def test_import_does_not_configure_node_logging(self):
        with open(
            os.path.join(os.path.dirname(__file__), "..", "edgeable", "node.py")
        ) as f:
            self.assertNotIn("basicConfig", f.read())

    def test_get_edges_accepts_any_callable(self):
        A, B, C = self.nodes("ABC")
        A.attach(B)
        A.attach(C)

        def to(id, edge):
            return edge.get_destination().get_id() == id

        class Matcher:
            def matches(self, edge):
                return to("C", edge)

            __call__ = matches

        self.assertEqual(len(A.get_edges(functools.partial(to, "B"))), 1)
        self.assertEqual(len(A.get_edges(Matcher().matches)), 1)
        self.assertEqual(len(A.get_edges(Matcher())), 1)
        self.assertEqual(len(A.get_edges(bool)), 2)
        with self.assertRaises(RuntimeError):
            A.get_edges("B")
        with self.assertRaises(RuntimeError):
            A.get_edges(None)

    def test_find_neighbors_validates_distance_fn(self):
        A, B = self.nodes("AB")
        A.attach(B)

        with self.assertRaises(RuntimeError):
            A.find_neighbors(1, distance_fn=None)
        with self.assertRaises(RuntimeError):
            A.find_neighbors(1, distance_fn=2)
        with self.assertRaises(RuntimeError):
            A.find_neighbors("far")
        self.assertEqual(A.find_neighbors(1, functools.partial(lambda e: 1)), [B])

    def test_get_edge_and_has_edge_ignore_unrelated_dangling_edges(self):
        A, B, C = self.nodes("ABC")
        A.attach(B)
        A.attach(C)
        # a dangling edge, as could be loaded from a file written by an
        # older version
        del self.db._graph["B"]

        self.assertTrue(A.has_edge(C))
        self.assertEqual(A.get_edge(C).get_destination(), C)
        self.assertTrue(A.has_edge(B))
        self.assertTrue(A.detach(B))
        self.assertFalse(A.has_edge(B))

    def test_get_edge_validates_destination(self):
        (A,) = self.nodes("A")
        with self.assertRaises(RuntimeError):
            A.get_edge("B")
        with self.assertRaises(RuntimeError):
            A.has_edge("B")

    def test_node_has_property_validates_key(self):
        (A,) = self.nodes("A")
        A.set_property("k", None)

        self.assertTrue(A.has_property("k"))
        self.assertFalse(A.has_property("other"))
        with self.assertRaises(RuntimeError):
            A.has_property(5)

    def test_edge_has_property_validates_key(self):
        A, B = self.nodes("AB")
        A.attach(B, {"k": None})
        edge = A.get_edge(B)

        self.assertTrue(edge.has_property("k"))
        self.assertFalse(edge.has_property("other"))
        with self.assertRaises(RuntimeError):
            edge.has_property(5)

    def test_node_set_properties_validates_keys(self):
        (A,) = self.nodes("A")
        with self.assertRaises(RuntimeError):
            A.set_properties({"ok": 1, 5: 2})
        with self.assertRaises(RuntimeError):
            A.set_properties(None)
        self.assertEqual(A.get_properties(), {})

    def test_edge_set_properties_validates_keys(self):
        A, B = self.nodes("AB")
        A.attach(B)
        with self.assertRaises(RuntimeError):
            A.get_edge(B).set_properties({"ok": 1, 5: 2})
        with self.assertRaises(RuntimeError):
            A.get_edge(B).set_properties(None)
        self.assertEqual(A.get_edge(B).get_properties(), {})
        self.assertEqual(B.get_edge(A).get_properties(), {})

    def test_delete_property_returns_previous_value(self):
        (A,) = self.nodes("A")
        A.set_property("k", "v")
        self.assertEqual(A.delete_property("k"), "v")
        self.assertIsNone(A.delete_property("k"))
        self.assertFalse(A.has_property("k"))
