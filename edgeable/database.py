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
    """Class representing the graph database."""

    def __init__(self, filename="graph.db", properties={}):
        if type(filename) is not str:
            raise RuntimeError("Filename must be a string.")
        if type(properties) is not dict:
            raise RuntimeError("Properties be a dict.")

        self._graph = {}
        self._properties = properties
        self._filename = filename

        if os.path.exists(filename):
            self.reload()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    def get_nodes(self, filter_fn=lambda node: True):
        """Return all nodes, or nodes which match the optional filter function."""
        if type(filter_fn) is not types.FunctionType:
            raise RuntimeError("Filter must be a function.")

        return [node for node in self._graph.values() if filter_fn(node)]

    def get_edges(
        self, edge_filter_fn=lambda edge: True, node_filter_fn=lambda node: True
    ):
        """Return all edges, or edges which match the optional filter function."""
        if type(edge_filter_fn) is not types.FunctionType:
            raise RuntimeError("Filter must be a function.")

        return [
            edge
            for edges in [
                node.get_edges() for node in self.get_nodes() if node_filter_fn(node)
            ]
            for edge in edges
            if edge_filter_fn(edge)
        ]

    def get_node(self, id):
        """Get the node with the provided id, or None if it does not exist."""
        return self._graph[id] if self.has_node(id) else None

    def has_node(self, id):
        """Boolean indicating if the node is defined."""
        return id in self._graph

    @GraphModifyLock
    def put_node(self, id, properties={}):
        """Create a node, or update it if it already exists. Returns the node."""
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
        """Set a database property."""
        if type(key) is not str and not int:
            raise RuntimeError("Key must be a string.")
        self._properties[key] = value

    @GraphModifyLock
    def set_properties(self, properties):
        """Set multiple properties from the provided dict. Properties not in the dict are not removed."""
        if type(properties) is not dict:
            raise RuntimeError("Properties be a dict.")
        self._properties = {**self._properties, **properties}

    def get_property(self, key):
        """Get the property value."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        return self._properties[key] if self.has_property(key) else None

    def get_properties(self):
        """Get a dict containing all properties and values."""
        return self._properties.copy()

    def has_property(self, key):
        """Boolean value indicating if the property is defined."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        return key in self._properties

    @GraphModifyLock
    def delete_property(self, key):
        """Delete a property if it is defined. Returns the previous value, or None."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        value = self.get_property(key)
        if self.has_property(key):
            del self._properties[key]
        return value

    def get_node_count(self):
        """Return the number of nodes."""
        return len(self._graph)

    def get_edge_count(self):
        """Return the number of edges."""
        return sum([len(self._graph[node]._edges) for node in self._graph])

    def reload(self):
        """Reload the database from the local filesystem."""

        logger.info("load from file '%s'", self._filename)
        with gzip.open(self._filename, "rb") as f:
            self._graph = pickle.load(f)

    @GraphReadLock
    def save(self):
        """Save the database to the local filesystem."""

        logger.info("save to file '%s'", self._filename)
        temp_file = tempfile.NamedTemporaryFile(
            prefix=self._filename,
            dir=os.path.dirname(self._filename), delete=False
        )
        with gzip.open(temp_file, "wb") as f:
            pickle.dump(self._graph, f, protocol=4)
        os.replace(temp_file.name, self._filename)
