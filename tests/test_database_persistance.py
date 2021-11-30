import unittest
import os
from edgeable import GraphDatabase


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_persistance(self):
        A = self.db.put_node("A")

        self.db.save()
        A.delete()
        self.assertEqual(self.db.get_node_count(), 0)

        self.db.reload()
        self.assertEqual(self.db.get_node_count(), 1)

        os.remove("graph.db")

    def test_with_statement(self):

        with GraphDatabase() as db:
            db.put_node("A")

        self.assertEqual(os.path.exists("graph.db"), True)
        os.remove("graph.db")

    def test_with_statement_custom_filename(self):

        with GraphDatabase(filename="custom.db") as db:
            db.put_node("A")

        self.assertEqual(os.path.exists("custom.db"), True)
        os.remove("custom.db")
