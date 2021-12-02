import unittest
import os
from edgeable import GraphDatabase


class TestDatabaseEvents(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_set_create_node_callback(self):

        id = self.db.on_create_node(
            lambda node: node.set_property("my_key", "my_value")
        )

        A = self.db.put_node("A")

        self.assertIsNotNone(id)
        self.assertEqual(A.get_properties(), {"my_key": "my_value"})

    def test_change_create_node_callback(self):

        id = self.db.on_create_node(
            lambda node: node.set_property("my_key", "my_value")
        )
        self.db.on_create_node(
            lambda node: node.set_property("my_key2", "my_value2"), id
        )

        A = self.db.put_node("A")

        self.assertEqual(A.get_properties(), {"my_key2": "my_value2"})

    def test_remove_create_node_callback(self):

        id = self.db.on_create_node(
            lambda node: node.set_property("my_key", "my_value")
        )
        self.db.on_create_node(None, id)

        A = self.db.put_node("A")

        self.assertEqual(A.get_properties(), {})

    def test_set_create_edge_callback(self):

        id = self.db.on_create_edge(
            lambda edge: edge.set_property("my_key", "my_value")
        )

        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        self.assertIsNotNone(id)
        self.assertEqual(A.get_edge(B).get_properties(), {"my_key": "my_value"})

    def test_change_create_edge_callback(self):

        id = self.db.on_create_edge(
            lambda edge: edge.set_property("my_key", "my_value")
        )
        self.db.on_create_edge(
            lambda edge: edge.set_property("my_key2", "my_value2"), id
        )

        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        self.assertEqual(A.get_edge(B).get_properties(), {"my_key2": "my_value2"})

    def test_remove_create_edge_callback(self):

        id = self.db.on_create_edge(
            lambda edge: edge.set_property("my_key", "my_value")
        )
        self.db.on_create_edge(None, id)

        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        self.assertEqual(A.get_edge(B).get_properties(), {})
