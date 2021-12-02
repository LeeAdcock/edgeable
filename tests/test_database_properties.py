import unittest
import os
from edgeable import GraphDatabase


class TestDatabaseProperties(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

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
        self.assertEqual(self.db.delete_property("my_key"), "my_value")
        self.assertEqual(self.db.has_property("my_key"), False)

    def test_delete_not_existing_property(self):
        self.assertEqual(self.db.delete_property("my_key"), None)
        self.assertEqual(self.db.has_property("my_key"), False)
