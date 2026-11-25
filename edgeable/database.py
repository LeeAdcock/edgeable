import gzip
import importlib
import logging
import numbers
import os
import pickle
import stat
import tempfile
import threading
import uuid

from edgeable.threadlock import GraphModifyLock, GraphReadLock
from edgeable.edge import GraphEdge
from edgeable.node import GraphNode

logger = logging.getLogger("edgeable")

# Marker and version of the persisted file layout. Files are a gzip compressed
# pickle of the tuple (_FORMAT_MARKER, _FORMAT_VERSION, graph, properties).
# Files written by earlier releases are a gzip compressed pickle of just the
# graph dict, and are still readable.
_FORMAT_MARKER = "edgeable"
_FORMAT_VERSION = 2

# Persistent id standing in for the owning database inside a persisted file.
_DATABASE_PERSISTENT_ID = "edgeable.GraphDatabase"

# Attributes of a database which are never pickled.
_TRANSIENT_ATTRIBUTES = frozenset(
    ["_on_create_node", "_on_delete_node", "_on_create_edge", "_on_delete_edge"]
    + ["_lock"]
)

# The only globals a persisted file may reference, as (module, name). Anything
# else is refused when loading, rather than imported and called.
_SAFE_GLOBALS = frozenset(
    [
        ("builtins", "set"),
        ("builtins", "frozenset"),
        ("builtins", "complex"),
        ("builtins", "bytearray"),
        ("builtins", "range"),
        ("builtins", "slice"),
        ("collections", "OrderedDict"),
        ("collections", "deque"),
        ("collections", "Counter"),
        ("datetime", "datetime"),
        ("datetime", "date"),
        ("datetime", "time"),
        ("datetime", "timedelta"),
        ("datetime", "timezone"),
        ("decimal", "Decimal"),
        ("fractions", "Fraction"),
        ("uuid", "UUID"),
    ]
)


class _LegacyDatabaseReference:
    """Inert stand-in for the GraphDatabase instances embedded in files written
    by earlier releases. The real class is never instantiated while loading;
    nodes and edges are re-bound to the loading database afterwards."""

    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def __init__(self, *args, **kwargs):
        pass


class _GraphPickler(pickle.Pickler):
    """Pickler which writes a reference in place of any database object, and
    refuses to write anything that could not be loaded again."""

    def persistent_id(self, obj):
        if isinstance(obj, GraphDatabase):
            return _DATABASE_PERSISTENT_ID
        return None

    # Called (on Python 3.8+) for everything which is not a plain None, bool,
    # int, float, str, bytes, tuple, list, dict, set, frozenset or bytearray.
    def reducer_override(self, obj):
        cls = obj if isinstance(obj, type) else type(obj)
        if cls not in _SAFE_CLASSES:
            raise pickle.PicklingError(
                "Cannot save a value of type '%s.%s', which is not a type that "
                "is permitted in a database file."
                % (getattr(cls, "__module__", "?"), getattr(cls, "__qualname__", cls))
            )
        return NotImplemented


class _GraphUnpickler(pickle.Unpickler):
    """Unpickler which only resolves an allowlist of classes, and resolves the
    database reference to the database which is loading the file."""

    def __init__(self, file, database):
        super().__init__(file)
        self._database = database

    def persistent_load(self, pid):
        if pid == _DATABASE_PERSISTENT_ID:
            return self._database
        raise pickle.UnpicklingError(
            "Unsupported persistent reference in database file."
        )

    def find_class(self, module, name):
        if (module, name) == ("edgeable.node", "GraphNode"):
            return GraphNode
        if (module, name) == ("edgeable.edge", "GraphEdge"):
            return GraphEdge
        if (module, name) == ("edgeable.database", "GraphDatabase"):
            return _LegacyDatabaseReference
        if (module, name) in _SAFE_GLOBALS:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(
            "Database file references '%s.%s', which is not a type that is "
            "permitted in a database file." % (module, name)
        )


_SAFE_CLASSES = frozenset(
    [GraphNode, GraphEdge]
    + [getattr(importlib.import_module(m), n) for (m, n) in _SAFE_GLOBALS]
)


def _is_filter(fn):
    return callable(fn)


class GraphDatabase:
    """Class representing the graph database."""

    def __init__(self, filename="graph.db", properties=None):
        if type(filename) is not str:
            raise RuntimeError("Filename must be a string.")
        if properties is not None and type(properties) is not dict:
            raise RuntimeError("Properties be a dict.")
        if properties is not None and any(type(key) is not str for key in properties):
            raise RuntimeError("Key must be a string.")

        self._graph = {}
        self._properties = {}
        self._filename = filename

        if os.path.exists(filename):
            self.reload()

        # explicitly provided properties take precedence over loaded ones
        if properties:
            self._properties.update(properties)

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)

        # callbacks and lock, also initialized for unpickled objects
        self._on_create_node = {}
        self._on_delete_node = {}
        self._on_create_edge = {}
        self._on_delete_edge = {}
        self._lock = threading.RLock()
        return self

    def __getstate__(self):
        return {
            k: v for (k, v) in self.__dict__.items() if k not in _TRANSIENT_ATTRIBUTES
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    @GraphReadLock
    def get_nodes(self, filter_fn=lambda node: True):
        """Return all nodes, or nodes which match the optional filter function."""
        if not _is_filter(filter_fn):
            raise RuntimeError("Filter must be a function.")

        # iterate a snapshot, the filter is allowed to modify the graph
        return [node for node in list(self._graph.values()) if filter_fn(node)]

    @GraphReadLock
    def get_edges(
        self, edge_filter_fn=lambda edge: True, node_filter_fn=lambda node: True
    ):
        """Return all edges, or edges which match the optional filter function."""
        if not _is_filter(edge_filter_fn) or not _is_filter(node_filter_fn):
            raise RuntimeError("Filter must be a function.")

        return [
            edge
            for edges in [
                node.get_edges() for node in self.get_nodes() if node_filter_fn(node)
            ]
            for edge in edges
            if edge_filter_fn(edge)
        ]

    @GraphReadLock
    def get_node(self, id):
        """Get the node with the provided id, or None if it does not exist."""
        return self._graph[id] if self.has_node(id) else None

    @GraphReadLock
    def has_node(self, id):
        """Boolean indicating if the node is defined."""
        return id in self._graph

    @GraphModifyLock
    def put_node(self, id, properties={}):
        """Create a node, or update it if it already exists. Returns the node."""
        if type(id) is not str and not isinstance(id, numbers.Number):
            raise RuntimeError("Node id must be a string or number.")
        if type(properties) is not dict:
            raise RuntimeError("Properties must be a dict.")

        if not self.has_node(id):
            logger.debug("create node '%s' (%s)", id, properties)
            node = GraphNode(self, id)
            node._properties = properties.copy()

            # run every create node event callback, any of them may cancel
            cancel = False
            for fn in list(self._on_create_node.values()):
                if fn(node) is False:
                    cancel = True

            if not cancel:
                self._graph[id] = node
            else:
                return None

        else:
            self._graph[id]._properties = {**self._graph[id]._properties, **properties}

        return self._graph[id]

    def _set_callback(self, callbacks, fn, id):
        """Register, replace or (when fn is None) remove an event callback."""
        if fn is not None and not callable(fn):
            raise RuntimeError("Callback must be a function or None.")

        if fn is None:
            # removal, which is a no-op for an id which is not registered
            if id is not None:
                callbacks.pop(id, None)
            return id

        if id is None:
            id = uuid.uuid1()
        callbacks[id] = fn
        return id

    @GraphModifyLock
    def on_create_node(self, fn, id=None):
        """Set, change or (with fn=None) remove a node creation callback."""
        return self._set_callback(self._on_create_node, fn, id)

    @GraphModifyLock
    def on_delete_node(self, fn, id=None):
        """Set, change or (with fn=None) remove a node deletion callback."""
        return self._set_callback(self._on_delete_node, fn, id)

    @GraphModifyLock
    def on_create_edge(self, fn, id=None):
        """Set, change or (with fn=None) remove an edge creation callback."""
        return self._set_callback(self._on_create_edge, fn, id)

    @GraphModifyLock
    def on_delete_edge(self, fn, id=None):
        """Set, change or (with fn=None) remove an edge deletion callback."""
        return self._set_callback(self._on_delete_edge, fn, id)

    @GraphModifyLock
    def set_property(self, key, value):
        """Set a database property."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        self._properties[key] = value

    @GraphModifyLock
    def set_properties(self, properties):
        """Set multiple properties from the provided dict. Properties not in the dict are not removed."""
        if type(properties) is not dict:
            raise RuntimeError("Properties be a dict.")
        if any(type(key) is not str for key in properties):
            raise RuntimeError("Key must be a string.")
        self._properties = {**self._properties, **properties}

    @GraphReadLock
    def get_property(self, key):
        """Get the property value."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        return self._properties[key] if self.has_property(key) else None

    @GraphReadLock
    def get_properties(self):
        """Get a dict containing all properties and values."""
        return self._properties.copy()

    @GraphReadLock
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

    @GraphReadLock
    def get_node_count(self):
        """Return the number of nodes."""
        return len(self._graph)

    @GraphReadLock
    def get_edge_count(self):
        """Return the number of edges."""
        return sum([len(self._graph[node]._edges) for node in self._graph])

    @GraphModifyLock
    def reload(self):
        """Reload the database from the local filesystem, replacing the nodes,
        edges and database properties held in memory. Registered callbacks are
        kept.

        Only edgeable's own classes and a fixed set of plain data types are
        permitted in the file; pickle.UnpicklingError is raised for anything
        else, and the database in memory is left unchanged."""

        logger.debug("load from file '%s'", self._filename)
        with gzip.open(self._filename, "rb") as f:
            content = _GraphUnpickler(f, self).load()

        if (
            type(content) is tuple
            and len(content) == 4
            and content[0] == _FORMAT_MARKER
        ):
            _, version, graph, properties = content
            if version != _FORMAT_VERSION:
                raise pickle.UnpicklingError(
                    "Unsupported database file version '%s'." % (version,)
                )
        else:
            # Written by an earlier release: only the graph was persisted, so
            # the properties of this database are left as they are.
            graph, properties = content, None

        if type(graph) is not dict or (
            properties is not None and type(properties) is not dict
        ):
            raise pickle.UnpicklingError("File is not an edgeable database.")

        # Bind everything loaded to this database. Earlier releases persisted a
        # copy of the database with the nodes, which they stayed attached to.
        for node in graph.values():
            if (
                type(node) is not GraphNode
                or type(vars(node).get("_edges")) is not dict
            ):
                raise pickle.UnpicklingError("File is not an edgeable database.")
            for edge in node._edges.values():
                if type(edge) is not GraphEdge:
                    raise pickle.UnpicklingError("File is not an edgeable database.")
                edge._db = self
            node._db = self

        self._graph = graph
        if properties is not None:
            self._properties = properties

    @GraphReadLock
    def save(self):
        """Save the database to the local filesystem.

        The content is written to a temporary file in the same directory, which
        then atomically replaces the database file."""

        logger.debug("save to file '%s'", self._filename)
        directory = os.path.dirname(self._filename) or os.curdir
        fd, temp_filename = tempfile.mkstemp(
            prefix=os.path.basename(self._filename) + ".", suffix=".tmp", dir=directory
        )
        try:
            with os.fdopen(fd, "wb") as temp_file:
                with gzip.GzipFile(fileobj=temp_file, mode="wb") as f:
                    _GraphPickler(f, protocol=4).dump(
                        (
                            _FORMAT_MARKER,
                            _FORMAT_VERSION,
                            self._graph,
                            self._properties,
                        )
                    )
                temp_file.flush()
                os.fsync(temp_file.fileno())

            # keep the permissions of a database file which is being replaced
            try:
                mode = stat.S_IMODE(os.stat(self._filename).st_mode)
            except FileNotFoundError:
                mode = None
            if mode is not None:
                os.chmod(temp_filename, mode)

            os.replace(temp_filename, self._filename)
        except BaseException:
            try:
                os.unlink(temp_filename)
            except OSError:
                pass
            raise
