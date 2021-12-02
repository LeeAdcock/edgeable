from edgeable import GraphEdge, GraphModifyLock
from collections import deque
import logging
import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edgeable")


class GraphNode:
    def __init__(self, db, id):
        self._db = db
        self._id = id
        self._properties = {}
        self._edges = {}

    def __eq__(self, other):
        if isinstance(other, GraphNode):
            return self.get_id() == other.get_id()
        return False

    def __str__(self):
        return self.get_id()

    def __repr__(self):
        return self.get_id()

    def __hash__(self):
        return hash(self.get_id())

    def get_id(self):
        return self._id

    @GraphModifyLock
    def attach(self, destination, properties={}, directed=False):
        """Attach this node to another node with an edge. Returns a boolean
        indicating if a new edge was created. Optionally provided properties
        will be set on the edge. Unless directed=True then this is
        mirrored onto an edge in the reverse direction."""

        if type(destination) is not GraphNode:
            raise RuntimeError("Destination must be an instance of GraphNode.")
        if type(properties) is not dict:
            raise RuntimeError("Properties must be a dict.")
        if not self._db.has_node(self._id):
            raise RuntimeError("Node does not existing in graph")
        if destination.get_id() == self._id:
            return False

        is_connected = destination.get_id() in self._edges
        if not is_connected:
            logger.info(
                "attach '%s' -> '%s' (%s)", self._id, destination.get_id(), properties
            )
            edge = GraphEdge(
                db=self._db, source=self, destination=destination, properties=properties
            )

            # run create edge callbacks
            cancel = False
            for fn in self._db._on_create_edge.values():
                cancel = cancel or (False == fn(edge))

            if not cancel:
                self._edges[destination.get_id()] = edge

                if not directed:
                    destination.attach(self, properties, directed=False)

        else:
            self._edges[destination.get_id()]._properties = {
                **self._edges[destination.get_id()]._properties,
                **properties,
            }

        return not is_connected

    @GraphModifyLock
    def detach(self, destination=None, directed=False):
        """Detach this node from another node. Returns a boolean
        indicating if an edge was removed. If no destination is provided
        then the node is detached fom all other nodes. Unless directed=True
        then this is mirrored onto an edge in the reverse direction."""

        if destination is not None and type(destination) is not GraphNode:
            raise RuntimeError("Destination must be an instance of GraphNode.")
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        if destination:
            was_connected = destination.get_id() in self._edges
            if was_connected:
                logger.info("detach '%s' from '%s'", self._id, destination.get_id())
                edge = self._edges[destination.get_id()]

                # run delete node callbacks
                cancel = False
                for fn in self._db._on_delete_edge.values():
                    cancel = cancel or (False == fn(edge))

                if not cancel:
                    del self._edges[destination.get_id()]

                    if not directed:
                        if self._id in self._db._graph[destination.get_id()]._edges:
                            self._db._graph[destination.get_id()].detach(self)

            return was_connected
        else:
            was_connected = False
            for edge in self.get_edges():
                was_connected = was_connected or self.detach(
                    edge.get_destination(), directed=directed
                )
        return was_connected

    @GraphModifyLock
    def delete(self):
        """Delete this node and all associated edges."""
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")

        # run delete node callbacks
        cancel = False
        for fn in self._db._on_delete_node.values():
            cancel = cancel or (False == fn(self))

        if not cancel:
            self.detach()
            del self._db._graph[self._id]

    @GraphModifyLock
    def set_property(self, key, value):
        """Set a node property."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        self._properties[key] = value

    @GraphModifyLock
    def set_properties(self, properties):
        """Set multiple properties from the provided dict. Properties not in the dict are not removed."""
        if type(properties) is not dict:
            raise RuntimeError("Key properties be a dict.")
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

    # Returns a list of edges
    def get_edges(self, filter_fn=lambda edge: True):
        """Return all edges, or edges which match the optional filter function."""
        if type(filter_fn) is not types.FunctionType:
            raise RuntimeError("Filter must be a function.")
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        return [edge for edge in self._edges.values() if filter_fn(edge)]

    # Returns an edge to the specified node
    def get_edge(self, destination):
        """Return the edge to the specified destination node, or None if one does not exist."""
        if type(destination) is not GraphNode:
            raise RuntimeError("Destination must be an instance of GraphNode.")
        edges = [
            edge
            for edge in self.get_edges()
            if edge.get_destination().get_id() == destination.get_id()
        ]
        if edges:
            return edges[0]

        return None

    # Returns an edge to the specified node
    def has_edge(self, destination):
        """Boolean whether an edge exists to the specified destination node."""
        if type(destination) is not GraphNode:
            raise RuntimeError("Destination must be an instance of GraphNode.")
        return any(
            edge.get_destination().get_id() == destination.get_id()
            for edge in self.get_edges()
        )

    # Returns a collection of less-optimal routes. The number of
    # these returned depends on the effort to find them, provided
    # as a numeric parameter.
    def find_routes_to(self, destination, effort=5):
        if type(destination) is not GraphNode:
            raise RuntimeError("Destination must be an instance of GraphNode.")
        q = deque([[]])
        routes = []
        while len(q):
            skip = q.popleft()
            route = self.find_route_to(destination, skip)
            if route and len(skip) <= effort:
                for step in route[1:-1]:
                    if (
                        not step == self._id
                        and not step == destination.get_id()
                        and not step in skip
                    ):
                        q.append(skip + [step])
                routes.append(route)

        deduped_routes = []
        [deduped_routes.append(x) for x in routes if x not in deduped_routes]
        return deduped_routes

    # Based on code by Eryk Kopczyński
    # https://www.python.org/doc/essays/graphs/
    def find_route_to(self, destination, skip=[]):
        """Find a route across the graph from the current node to the
        destination node, returned as an array of nodes. If no route
        exists, returns None."""

        if type(destination) is not GraphNode:
            raise RuntimeError("Destination must be an instance of GraphNode.")
        dist = {self: [self]}
        q = deque([self])
        while len(q):
            node = q.popleft()
            for edge in node.get_edges():
                next_node = edge.get_destination()
                if (
                    next_node not in dist
                    and destination not in dist
                    and next_node not in skip
                ):
                    dist[next_node] = [
                        dist[node],
                        next_node,
                    ]
                    q.append(next_node)

        def flatten(route):
            return route if len(route) == 1 else flatten(route[0]) + [route[1]]

        return flatten(dist[destination]) if destination in dist else None

    def find_neighbors(self, distance=1, distance_fn=lambda edge: 1):
        """Find all neighbors the specified distance away."""

        dist = {self: 0}
        q = deque([self])
        while len(q):
            node = q.popleft()
            for edge in node.get_edges():
                next_node = edge.get_destination()
                if next_node not in dist:
                    edge_distance = distance_fn(edge)
                    if dist[node] + edge_distance <= distance:
                        dist[next_node] = dist[node] + edge_distance
                        q.append(next_node)

        return list(dist.keys())[1:]
