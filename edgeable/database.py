import pickle
import logging

from edgeable import GraphNode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edgeable")


class GraphDatabase:
    def __init__(self, filename="graph.db"):
        self.graph = {}
        self.filename = filename

    def get_nodes(self, criteria=lambda node: True):
        return [
            GraphNode(self, node)
            for node in self.graph
            if criteria(GraphNode(self, node))
        ]

    def has_node(self, id):
        return id in self.graph

    # Retrieves or creates a node with the provide id
    def get_node(self, id, properties={}):
        if not isinstance(id, str):
            raise "Node id must be a string."

        if not self.has_node(id):
            logger.info("create node '%s'", id)
            self.graph[id] = {"connections": {}, "meta": properties}
        else:
            self.graph[id]["meta"] = {**self.graph[id]["meta"], **properties}

        return GraphNode(self, id)

    def get_node_count(self):
        return len(self.graph)

    def get_edge_count(self):
        return sum([len(self.graph[node]) for node in self.graph])

    def load(self):
        with open(self.filename, "rb") as f:
            self.graph = pickle.load(f)

    def save(self):
        with open(self.filename, "wb") as f:
            pickle.dump(self.graph, f, protocol=pickle.DEFAULT_PROTOCOL)
