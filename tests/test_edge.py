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
