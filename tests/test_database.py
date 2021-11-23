import unittest
from edgeable import GraphDatabase


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_add_node(self):
        A = self.db.get_node("A")
        self.assertEqual(A.get_properties(), {})

        B = self.db.get_node("B", {"my_key": "my_value"})
        self.assertEqual(B.get_properties(), {"my_key": "my_value"})

        B = self.db.get_node("B", {"my_key_2": "my_value_2"})
        self.assertEqual(
            B.get_properties(), {"my_key": "my_value", "my_key_2": "my_value_2"}
        )

    def test_has_node(self):
        self.db.get_node("A")

        self.assertEqual(self.db.has_node("A"), True)
        self.assertEqual(self.db.has_node("B"), False)

    def test_get_node_count(self):
        self.db.get_node("A")
        self.db.get_node("B")

        self.assertEqual(self.db.get_node_count(), 2)

    def test_get_edge_count(self):
        A = self.db.get_node("A")
        B = self.db.get_node("B")
        A.attach(B)

        self.assertEqual(self.db.get_edge_count(), 4)

    def test_get_nodes(self):
        self.db.get_node("A")
        self.db.get_node("B")

        self.assertEqual(len(self.db.get_nodes()), 2)
        self.assertEqual(len(self.db.get_nodes(lambda node: node.get_id() == "A")), 1)

    def test_add_node_with_properties(self):
        A = self.db.get_node("A", {"my_key": "my_value"})
        self.assertEqual(A.get_properties(), {"my_key": "my_value"})

    def test_add_node_overwrite_properties(self):
        A = self.db.get_node("A", {"my_key": "my_value"})
        A = self.db.get_node("A", {"my_key_2": "my_value_2"})
        self.assertEqual(
            A.get_properties(), {"my_key": "my_value", "my_key_2": "my_value_2"}
        )

    def test_persistance(self):
        self.db.set_filename("./tests/graph.db")
        A = self.db.get_node("A", {"my_key": "my_value"})
        B = self.db.get_node("B", {"my_key_2": "my_value_2"})
        A.attach(B)

        self.db.save()
        A.delete()
        self.assertEqual(self.db.get_node_count(), 1)

        self.db.load()
        self.assertEqual(self.db.get_node_count(), 2)
