import unittest
from edgeable import GraphDatabase


class TestNode(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_eq(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")

        self.assertEqual(A, A)
        self.assertNotEqual(A, B)

    def test_str(self):
        A = self.db.put_node("A")

        self.assertEqual(str(A), "A")

    def test_attach_node(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)
        self.assertEqual(len(A.get_edges()), 1)
        self.assertEqual(len(B.get_edges()), 1)

        self.assertEqual(A.get_edge(B).get_destination().get_id(), B.get_id())
        self.assertEqual(B.get_edge(A).get_destination().get_id(), A.get_id())

    def test_attach_node_directed(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B, directed=True)
        self.assertEqual(len(A.get_edges()), 1)
        self.assertEqual(len(B.get_edges()), 0)

        self.assertEqual(A.get_edge(B).get_destination().get_id(), B.get_id())

    def test_get_edges(self):
        A = self.db.put_node("A")

        B = self.db.put_node("B")
        B.attach(A)

        C = self.db.put_node("C")
        C.attach(A)

        self.assertEqual(len(A.get_edges()), 2)
        self.assertEqual(
            len(A.get_edges(lambda edge: edge.get_destination().get_id() == "B")), 1
        )

    def test_node_has_edge(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        C = self.db.put_node("C")
        B.attach(A)

        self.assertEqual(A.has_edge(B), True)
        self.assertEqual(B.has_edge(A), True)
        self.assertEqual(A.has_edge(C), False)
        self.assertEqual(B.has_edge(C), False)

    def test_attach_node_overwrite_properties(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B, {"my_key": "my_value"})
        A.attach(B, {"my_key_2": "my_value_2"})

        self.assertEqual(
            A.get_edge(B).get_properties(),
            {"my_key": "my_value", "my_key_2": "my_value_2"},
        )

    def test_get_edge(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        self.assertEqual(A.get_edge(B).get_destination(), B)
        self.assertEqual(A.get_edge(B).get_source(), A)

        self.assertEqual(B.get_edge(A).get_destination(), A)
        self.assertEqual(A.get_edge(B).get_source(), A)

    def test_get_edge_doesnt_exist(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")

        self.assertEqual(A.get_edge(B), None)

    def test_attach_node_with_properties(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B, {"my_key": "my_value"})
        self.assertEqual(A.get_edge(B).get_property("my_key"), "my_value")
        self.assertEqual(B.get_edge(A).get_property("my_key"), "my_value")

    def test_detach_node(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        self.db.put_node("B").detach()
        self.assertEqual(len(A.get_edges()), 0)
        self.assertEqual(len(B.get_edges()), 0)
        self.assertEqual(self.db.get_node_count(), 2)

    def test_detach_node_not_attached(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")

        self.assertEqual(A.detach(B), False)

    def test_detach_node_directed(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        self.db.put_node("B").detach(directed=True)
        self.assertEqual(len(A.get_edges()), 1)
        self.assertEqual(len(B.get_edges()), 0)
        self.assertEqual(self.db.get_node_count(), 2)

    def test_delete_node(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        A.delete()

        self.assertEqual(self.db.get_node_count(), 1)
        self.assertEqual(len(B.get_edges()), 0)
