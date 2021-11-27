import unittest
from edgeable import GraphDatabase


class TestNode(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_node_get_set_property(self):
        A = self.db.put_node("A")
        A.set_property("my_key", "my_value")

        self.assertEqual(A.get_property("my_key"), "my_value")

    def test_node_get_properties(self):
        A = self.db.put_node("A")
        A.set_property("my_key", "my_value")

        properties = A.get_properties()
        self.assertEqual(properties, {"my_key": "my_value"})

    def test_node_properties_returns_copy(self):
        A = self.db.put_node("A")
        A.set_property("my_key", "my_value")

        properties = A.get_properties()
        properties["my_key_2"] = "my_value_2"
        self.assertEqual(A.get_properties(), {"my_key": "my_value"})

    def test_node_has_property(self):
        A = self.db.put_node("A")
        A.set_property("my_key", "my_value")

        self.assertEqual(A.has_property("my_key"), True)
        self.assertEqual(A.has_property("my_key_2"), False)

    def test_node_set_properties(self):
        A = self.db.put_node("A")
        A.set_properties({"my_key": "my_value"})

        self.assertEqual(A.has_property("my_key"), True)
        self.assertEqual(A.has_property("my_key_2"), False)

    def test_node_delete_property(self):
        A = self.db.put_node("A")
        A.set_property("my_key", "my_value")

        self.assertEqual(A.delete_property("my_key"), "my_value")
        self.assertEqual(A.has_property("my_key"), False)

    def test_node_delete__not_existing_property(self):
        A = self.db.put_node("A")

        self.assertEqual(A.delete_property("my_key"), None)
        self.assertEqual(A.has_property("my_key"), False)
