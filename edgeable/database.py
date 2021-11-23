import pickle
import logging
import gzip
import types

from edgeable import GraphNode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edgeable")


class GraphDatabase:
    def __init__(self, filename="graph.db"):
        if type(filename) is not str:
            raise RuntimeError("Filename must be a string.")
        self._graph = {}
        self._filename = filename

    def get_nodes(self, criteria=lambda node: True):
        if type(criteria) is not types.FunctionType:
            raise RuntimeError("Criteria must be a function.")

        return [node for node in self._graph.values() if criteria(node)]

    def has_node(self, id):
        return id in self._graph

    # Retrieves or creates a node with the provide id
    def put_node(self, id, properties={}):
        if type(id) is not str:
            raise RuntimeError("Node id must be a string.")

        if not self.has_node(id):
            logger.info("create node '%s'", id)
            self._graph[id] = GraphNode(self, id)
            self._graph[id]._properties = properties.copy()
        else:
            self._graph[id]._properties = {**self._graph[id]._properties, **properties}

        return self._graph[id]

    def get_node_count(self):
        return len(self._graph)

    def get_edge_count(self):
        return sum([len(self._graph[node]._edges) for node in self._graph])

    def load(self):
        with gzip.open(self._filename, "rb") as f:
            self._graph = pickle.load(f)

    def save(self):
        with gzip.open(self._filename, "wb") as f:
            pickle.dump(self._graph, f, protocol=4)
