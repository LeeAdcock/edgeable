import unittest
from edgeable import GraphDatabase


class TestEdge(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_eq(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        C = self.db.put_node("C")
        A.attach(B)
        B.attach(C)

        self.assertEqual(A.get_edge(B), A.get_edge(B))
        self.assertNotEqual(A.get_edge(B), B.get_edge(C))

    def test_str(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        self.assertEqual(str(A.get_edge(B)), "A->B")

    def test_edge_get_set_property(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        A.get_edge(B).set_property("my_key", "my_value_new")
        A.get_edge(B).set_property("my_key_2", "my_value_2")

        self.assertEqual(A.get_edge(B).get_property("my_key"), "my_value_new")
        self.assertEqual(B.get_edges()[0].get_property("my_key_2"), "my_value_2")

    def test_edge_get_set_property_directed(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        A.get_edge(B).set_property("my_key", "my_value_new", directed=True)

        self.assertEqual(A.get_edge(B).get_property("my_key"), "my_value_new")
        self.assertEqual(B.get_edge(A).get_property("my_key"), None)

    def test_edge_with_properties(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B, {"my_key": "my_value"})

        A.get_edge(B).set_property("my_key", "my_value_new")
        A.get_edge(B).set_property("my_key_2", "my_value_2")

        self.assertEqual(
            A.get_edge(B).get_properties(),
            {"my_key": "my_value_new", "my_key_2": "my_value_2"},
        )

    def test_edge_properties_returns_copy(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B, {"my_key": "my_value"})

        edge = A.get_edge(B)
        properties = edge.get_properties()
        properties["my_key_2"] = "my_value_2"
        self.assertEqual(
            edge.get_properties(),
            {"my_key": "my_value"},
        )

    def test_edge_set_properties(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)
        edge = A.get_edge(B)
        edge.set_properties({"my_key": "my_value"})
        self.assertEqual(
            edge.get_properties(),
            {"my_key": "my_value"},
        )

    def test_edge_set_properties_directed(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        A.get_edge(B).set_properties({"my_key": "my_value"}, directed=True)
        self.assertEqual(
            A.get_edge(B).get_property("my_key"),
            "my_value",
        )
        self.assertEqual(
            B.get_edge(A).get_property("my_key"),
            None,
        )

    def test_edge_has_property(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B, {"my_key": "my_value"})
        edge = A.get_edge(B)

        self.assertEqual(edge.has_property("my_key"), True)
        self.assertEqual(edge.has_property("my_key_2"), False)

    def test_edge_delete_property(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B, {"my_key": "my_value"})
        edge = A.get_edge(B)

        self.assertEqual(edge.delete_property("my_key"), "my_value")
        self.assertEqual(edge.has_property("my_key"), False)

    def test_edge_delete_not_existing_property(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)
        edge = A.get_edge(B)

        self.assertEqual(edge.delete_property("my_key"), None)
        self.assertEqual(edge.has_property("my_key"), False)

    def test_edge_delete(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        edge = A.get_edge(B)
        edge.delete()

        self.assertEqual(len(A.get_edges()), 0)
        self.assertEqual(len(B.get_edges()), 0)

    def test_edge_delete_directed(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        edge = A.get_edge(B)
        edge.delete(directed=True)

        self.assertEqual(len(A.get_edges()), 0)
        self.assertEqual(len(B.get_edges()), 1)
