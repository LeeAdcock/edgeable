import unittest
from edgeable import GraphDatabase


class TestNodeNeighbors(unittest.TestCase):
    def setUp(self):
        self.db = GraphDatabase()

    def test_node_neighbors(self):
        A = self.db.put_node("A")

        B = self.db.put_node("B")
        B.attach(A)

        C = self.db.put_node("C")
        C.attach(B)

        D = self.db.put_node("D")
        D.attach(C)

        self.assertEqual(A.find_neighbors(distance=1), [B])
        self.assertEqual(A.find_neighbors(distance=2), [B, C])
        self.assertEqual(A.find_neighbors(distance=3), [B, C, D])

    def test_node_neighbors_custom_distance(self):
        A = self.db.put_node("A")

        B = self.db.put_node("B")
        B.attach(A, {"distance": 2})

        C = self.db.put_node("C")
        C.attach(B, {"distance": 2})

        D = self.db.put_node("D")
        D.attach(C, {"distance": 2})

        fn = lambda e: e.get_property("distance")

        self.assertEqual(A.find_neighbors(distance=1, distance_fn=fn), [])
        self.assertEqual(A.find_neighbors(distance=2, distance_fn=fn), [B])
        self.assertEqual(A.find_neighbors(distance=3, distance_fn=fn), [B])
        self.assertEqual(A.find_neighbors(distance=4, distance_fn=fn), [B, C])
        self.assertEqual(A.find_neighbors(distance=5, distance_fn=fn), [B, C])
        self.assertEqual(A.find_neighbors(distance=6, distance_fn=fn), [B, C, D])

    def test_node_no_neighbors(self):
        A = self.db.put_node("A")

        self.assertEqual(A.find_neighbors(distance=3), [])
