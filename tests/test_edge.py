import unittest
from edgeable import GraphDatabase


class TestEdge(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_edge_get_set_property(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B)

        A.get_edges()[0].set_property("my_key", "my_value_new")
        A.get_edges()[0].set_property("my_key_2", "my_value_2")

        self.assertEqual(A.get_edges()[0].get_property("my_key"), "my_value_new")
        self.assertEqual(B.get_edges()[0].get_property("my_key_2"), "my_value_2")

    def test_edge_get_set_property_directed(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B)

        A.get_edges()[0].set_property("my_key", "my_value_new", directed=True)

        self.assertEqual(A.get_edges()[0].get_property("my_key"), "my_value_new")
        self.assertEqual(B.get_edges()[0].get_property("my_key"), None)

    def test_edge_with_properties(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B, {"my_key": "my_value"})

        A.get_edges()[0].set_property("my_key", "my_value_new")
        A.get_edges()[0].set_property("my_key_2", "my_value_2")

        self.assertEqual(
            A.get_edges()[0].get_properties(),
            {"my_key": "my_value_new", "my_key_2": "my_value_2"},
        )

    def test_edge_properties_returns_copy(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B, {"my_key": "my_value"})

        edge = A.get_edges()[0]
        properties = edge.get_properties()
        properties["my_key_2"] = "my_value_2"
        self.assertEqual(
            edge.get_properties(),
            {"my_key": "my_value"},
        )

    def test_edge_delete(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B)

        edge = A.get_edges()[0]
        edge.delete()

        self.assertEqual(len(A.get_edges()), 0)
        self.assertEqual(len(B.get_edges()), 0)

    def test_edge_delete_directed(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B)

        edge = A.get_edges()[0]
        edge.delete(directed=True)

        self.assertEqual(len(A.get_edges()), 0)
        self.assertEqual(len(B.get_edges()), 1)
