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

    def test_create_node_callback_cancels(self):

        self.db.on_create_node(lambda node: False)

        self.db.put_node("A")

        self.assertFalse(self.db.has_node("A"))

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

    def test_create_edge_callback_cancels(self):

        self.db.on_create_edge(lambda node: False)

        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        self.assertIsNone(A.get_edge(B))

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

    def test_set_delete_node_callback(self):

        self.db.on_delete_node(lambda node: self.db.put_node(node.get_id() + "2"))

        self.db.put_node("A").delete()

        self.assertTrue(self.db.has_node("A2"))

    def test_delete_node_callback_cancels(self):

        self.db.on_delete_node(lambda node: False)

        self.db.put_node("A").delete()

        self.assertTrue(self.db.has_node("A"))

    def test_change_delete_node_callback(self):

        id = self.db.on_delete_node(lambda node: self.db.put_node(node.get_id() + "2"))

        self.db.on_delete_node(lambda node: self.db.put_node(node.get_id() + "3"), id)

        self.db.put_node("A").delete()

        self.assertTrue(self.db.has_node("A3"))

    def test_remove_delete_node_callback(self):

        id = self.db.on_delete_node(lambda node: self.db.put_node(node.get_id() + "2"))

        self.db.on_delete_node(None, id)

        self.db.put_node("A").delete()

        self.assertFalse(self.db.has_node("A2"))

    def test_set_delete_edge_callback(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        C = self.db.put_node("C")
        A.attach(B)

        id = self.db.on_delete_edge(lambda edge: edge.get_source().attach(C))

        A.get_edge(B).delete()

        self.assertIsNotNone(id)
        self.assertIsNotNone(A.get_edge(C))

    def test_delete_edge_callback_cancels(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        A.attach(B)

        self.db.on_delete_edge(lambda node: False)

        A.get_edge(B).delete()

        self.assertIsNotNone(A.get_edge(B))

    def test_change_delete_edge_callback(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        C = self.db.put_node("C")
        D = self.db.put_node("D")
        A.attach(B)

        id = self.db.on_delete_edge(lambda edge: edge.get_source().attach(C))
        self.db.on_delete_edge(lambda edge: edge.get_source().attach(D), id)

        A.get_edge(B).delete()

        self.assertIsNotNone(A.get_edge(D))

    def test_remove_delete_edge_callback(self):
        A = self.db.put_node("A")
        B = self.db.put_node("B")
        C = self.db.put_node("C")
        A.attach(B)

        id = self.db.on_delete_edge(lambda edge: edge.get_source().attach(C))
        self.db.on_delete_edge(None, id)

        A.get_edge(B).delete()

        self.assertIsNone(A.get_edge(C))
