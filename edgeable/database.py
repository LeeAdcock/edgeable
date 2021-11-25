import pickle
import logging
import gzip
import types
import os
import tempfile
import numbers

from edgeable import GraphNode, GraphModifyLock, GraphReadLock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edgeable")


class GraphDatabase:
    def __init__(self, filename="graph.db", properties={}):
        if type(filename) is not str:
            raise RuntimeError("Filename must be a string.")
        self._graph = {}
        self._filename = filename
        self._properties = properties

    def get_nodes(self, criteria=lambda node: True):
        if type(criteria) is not types.FunctionType:
            raise RuntimeError("Criteria must be a function.")

        return [node for node in self._graph.values() if criteria(node)]

    def get_node(self, id):
        return self._graph[id] if self.has_node(id) else None

    def has_node(self, id):
        return id in self._graph

    # Retrieves or creates a node with the provide id
    @GraphModifyLock
    def put_node(self, id, properties={}):
        if type(id) is not str and not isinstance(id, numbers.Number):
            raise RuntimeError("Node id must be a string or number.")

        if not self.has_node(id):
            logger.info("create node '%s'", id)
            self._graph[id] = GraphNode(self, id)
            self._graph[id]._properties = properties.copy()
        else:
            self._graph[id]._properties = {**self._graph[id]._properties, **properties}

        return self._graph[id]

    @GraphModifyLock
    def set_property(self, key, value):
        if type(key) is not str and not int:
            raise RuntimeError("Key must be a string.")
        self._properties[key] = value

    @GraphModifyLock
    def set_properties(self, properties):
        if type(properties) is not dict:
            raise RuntimeError("Properties be a dict. {}".format(type(properties)))
        self._properties = {**self._properties, **properties}

    def get_property(self, key):
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        return self._properties[key] if self.has_property(key) else None

    def get_properties(self):
        return self._properties.copy()

    def has_property(self, key):
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        return key in self._properties

    @GraphModifyLock
    def delete_property(self, key):
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        value = self.get_property(key)
        if self.has_property(key):
            del self._properties[key]
        return value

    def get_node_count(self):
        return len(self._graph)

    def get_edge_count(self):
        return sum([len(self._graph[node]._edges) for node in self._graph])

    def load(self):
        logger.info("load from file '%s'", self._filename)
        with gzip.open(self._filename, "rb") as f:
            self._graph = pickle.load(f)

    @GraphReadLock
    def save(self):
        logger.info("save to file '%s'", self._filename)
        temp_file = tempfile.NamedTemporaryFile(
            dir=os.path.dirname(self._filename), delete=False
        )
        with gzip.open(temp_file, "wb") as f:
            pickle.dump(self._graph, f, protocol=4)
        os.replace(temp_file.name, self._filename)
