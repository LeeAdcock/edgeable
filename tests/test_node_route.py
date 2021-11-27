import unittest
from edgeable import GraphDatabase


class TestNode(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_node_route(self):
        A = self.db.put_node("A")

        B = self.db.put_node("B")
        B.attach(A)

        C = self.db.put_node("C")
        C.attach(B)

        D = self.db.put_node("D")
        D.attach(C)

        self.assertEqual(A.find_route_to(B), [A, B])
        self.assertEqual(A.find_route_to(C), [A, B, C])

        self.assertEqual(C.find_route_to(A), [C, B, A])
        self.assertEqual(B.find_route_to(A), [B, A])

    def test_node_route_circular(self):
        A = self.db.put_node("A")

        B = self.db.put_node("B")
        B.attach(A)

        C = self.db.put_node("C")
        C.attach(B)

        D = self.db.put_node("D")
        D.attach(C)
        D.attach(A)

        self.assertEqual(A.find_route_to(D), [A, D])
        self.assertEqual(D.find_route_to(A), [D, A])

    def test_node_route_directed(self):
        A = self.db.put_node("A")

        B = self.db.put_node("B")
        B.attach(A, directed=True)

        C = self.db.put_node("C")
        C.attach(B, directed=True)

        D = self.db.put_node("D")
        D.attach(C, directed=True)
        A.attach(D, directed=True)

        self.assertEqual(A.find_route_to(D), [A, D])
        self.assertEqual(D.find_route_to(A), [D, C, B, A])

    def test_node_routes(self):
        A = self.db.put_node("A")

        B = self.db.put_node("B")
        B.attach(A)

        C = self.db.put_node("C")
        C.attach(A)

        D = self.db.put_node("D")
        D.attach(C)
        D.attach(B)

        self.assertEqual(A.find_routes_to(D), [[A, B, D], [A, C, D]])
