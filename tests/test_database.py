import unittest
import os
from edgeable import GraphDatabase


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_add_node(self):
        A = self.db.put_node("A")
        self.assertEqual(A.get_properties(), {})

        B = self.db.put_node("B", {"my_key": "my_value"})
        self.assertEqual(B.get_properties(), {"my_key": "my_value"})

        B = self.db.put_node("B", {"my_key_2": "my_value_2"})
        self.assertEqual(
            B.get_properties(), {"my_key": "my_value", "my_key_2": "my_value_2"}
        )

    def test_has_node_string_id(self):
        self.db.put_node("A")

        self.assertEqual(self.db.has_node("A"), True)
        self.assertEqual(self.db.has_node("B"), False)

    def test_has_node_number_id(self):
        self.db.put_node(123)

        self.assertEqual(self.db.has_node(123), True)

    def test_get_node_count(self):
        self.db.put_node("A")
        self.db.put_node("B")

        self.assertEqual(self.db.get_node_count(), 2)

    def test_get_edge_count(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        self.assertEqual(self.db.get_edge_count(), 2)

    def test_get_nodes(self):
        A = self.db.put_node("A", {"flag": True})
        self.db.put_node("B")

        nodes = self.db.get_nodes(lambda node: node.get_property("flag"))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0], A)

    def test_add_node_with_properties(self):
        A = self.db.put_node("A", {"my_key": "my_value"})
        self.assertEqual(A.get_properties(), {"my_key": "my_value"})

    def test_add_node_overwrite_properties(self):
        A = self.db.put_node("A", {"my_key": "my_value"})
        A = self.db.put_node("A", {"my_key_2": "my_value_2"})
        self.assertEqual(
            A.get_properties(), {"my_key": "my_value", "my_key_2": "my_value_2"}
        )

    def test_persistance(self):
        A = self.db.put_node("A")

        self.db.save()
        A.delete()
        self.assertEqual(self.db.get_node_count(), 0)

        self.db.load()
        self.assertEqual(self.db.get_node_count(), 1)

        os.remove("graph.db")

    def test_persistance_custom_filename(self):

        A = self.db.put_node("A")
        filename = "custom.db"

        self.db.save(filename=filename)
        A.delete()

        self.assertEqual(self.db.get_node_count(), 0)
        self.assertEqual(os.path.exists(filename), True)

        self.db.load(filename)
        self.assertEqual(self.db.get_node_count(), 1)

        os.remove(filename)

    def test_get_set_property(self):
        self.db.set_property("my_key", "my_value")
        self.assertEqual(self.db.get_property("my_key"), "my_value")

    def test_get_properties(self):
        self.db.set_property("my_key", "my_value")

        properties = self.db.get_properties()
        self.assertEqual(properties, {"my_key": "my_value"})

    def test_properties_returns_copy(self):
        self.db.set_property("my_key", "my_value")

        properties = self.db.get_properties()
        properties["my_key_2"] = "my_value_2"
        self.assertEqual(self.db.get_properties(), {"my_key": "my_value"})

    def test_has_property(self):
        self.db.set_property("my_key", "my_value")
        self.assertEqual(self.db.has_property("my_key"), True)
        self.assertEqual(self.db.has_property("my_key_2"), False)

    def test_set_properties(self):
        self.db.set_properties({"my_key": "my_value"})
        self.assertEqual(self.db.has_property("my_key"), True)
        self.assertEqual(self.db.has_property("my_key_2"), False)

    def test_delete_property(self):
        self.db.set_property("my_key", "my_value")
        self.db.delete_property("my_key")
        self.assertEqual(self.db.has_property("my_key"), False)
