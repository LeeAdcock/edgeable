from collections import deque
import heapq
import logging
import math
import numbers

from edgeable.threadlock import GraphModifyLock, GraphReadLock
from edgeable.edge import GraphEdge

logger = logging.getLogger("edgeable")


def _validate_properties(properties):
    if type(properties) is not dict:
        raise RuntimeError("Properties must be a dict.")
    for key in properties:
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")


class GraphNode:
    """Class representing nodes in the graph."""

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
        return str(self._id)

    def __repr__(self):
        return str(self._id)

    def __hash__(self):
        return hash(self.get_id())

    def get_id(self):
        return self._id

    def _is_member(self):
        """Whether this exact object is the node stored in the graph."""
        return self._db._graph.get(self._id) is self

    @GraphModifyLock
    def attach(self, destination, properties=None, directed=False):
        """Attach this node to another node with an edge. Returns a boolean
        indicating if a new edge was created. Optionally provided properties
        will be set on the edge, whether it exists or is created new. Unless
        directed=True then this is mirrored onto an edge in the reverse
        direction. If a create edge callback cancels the operation nothing
        is changed (in either direction) and False is returned."""

        if not isinstance(destination, GraphNode):
            raise RuntimeError("Destination must be an instance of GraphNode.")
        if properties is None:
            properties = {}
        _validate_properties(properties)
        if not self._is_member():
            raise RuntimeError("Node does not exist in graph")
        if destination is self:
            return False
        if (
            not destination._is_member()
            or destination._db._graph is not self._db._graph
        ):
            raise RuntimeError("Destination node does not exist in graph")

        pairs = [(self, destination)]
        if not directed:
            pairs.append((destination, self))

        # Build every edge which is missing, and let the callbacks see all
        # of them before anything is changed, so that the operation is
        # applied in both directions or not at all.
        new_edges = {}
        for source, target in pairs:
            if target._id not in source._edges:
                logger.debug(
                    "attach '%s' -> '%s' (%s)", source._id, target._id, properties
                )
                new_edges[source._id] = GraphEdge(
                    db=self._db,
                    source=source,
                    destination=target,
                    properties=properties,
                )

        # run create edge callbacks
        cancel = False
        for edge in new_edges.values():
            for fn in list(self._db._on_create_edge.values()):
                if fn(edge) is False:
                    cancel = True
        if cancel:
            return False

        # a callback may have removed one of the nodes
        if not self._is_member() or not destination._is_member():
            return False

        created = False
        for source, target in pairs:
            edge = source._edges.get(target._id)
            if edge is None:
                edge = new_edges.get(source._id)
                if edge is None:
                    edge = GraphEdge(
                        db=self._db,
                        source=source,
                        destination=target,
                        properties=properties,
                    )
                source._edges[target._id] = edge
                created = True
            else:
                edge._properties.update(properties)

        return created

    def _detach_id(self, destination_id, directed):
        """Remove the edge to the node with the provided id, and unless
        directed the edge in the reverse direction. All or nothing: if a
        delete edge callback cancels, neither is removed. Returns whether an
        edge was removed. Callers must hold the modify lock."""
        targets = []
        edge = self._edges.get(destination_id)
        if edge is not None:
            targets.append((self, destination_id, edge))
        if not directed:
            other = self._db._graph.get(destination_id)
            if other is not None and other is not self:
                edge = other._edges.get(self._id)
                if edge is not None:
                    targets.append((other, self._id, edge))
        if not targets:
            return False

        # run delete edge callbacks
        cancel = False
        for owner, key, edge in targets:
            logger.debug("detach '%s' from '%s'", owner._id, key)
            for fn in list(self._db._on_delete_edge.values()):
                if fn(edge) is False:
                    cancel = True
        if cancel:
            return False

        removed = False
        for owner, key, edge in targets:
            # a callback may already have removed or replaced the edge
            if owner._edges.get(key) is edge:
                del owner._edges[key]
                removed = True
        return removed

    @GraphModifyLock
    def detach(self, destination=None, directed=False):
        """Detach this node from another node. Returns a boolean
        indicating if an edge was removed. If no destination is provided
        then the node is detached fom all other nodes. Unless directed=True
        then this is mirrored onto an edge in the reverse direction. If a
        delete edge callback cancels, neither direction is removed."""

        if destination is not None and not isinstance(destination, GraphNode):
            raise RuntimeError("Destination must be an instance of GraphNode.")
        if not self._is_member():
            raise RuntimeError("Node does not exist in graph")

        if destination is not None:
            return self._detach_id(destination.get_id(), directed)

        was_connected = False
        for destination_id in list(self._edges):
            if self._detach_id(destination_id, directed):
                was_connected = True
        return was_connected

    @GraphModifyLock
    def delete(self):
        """Delete this node and all associated edges, including edges on
        other nodes which point at this node. Returns a boolean indicating
        if the node was deleted.

        A delete node callback returning False cancels the deletion. Delete
        edge callbacks are then called for every edge being removed, but
        their return value is ignored: once the node is being deleted its
        edges always go with it."""
        graph = self._db._graph
        if not self._is_member():
            raise RuntimeError("Node does not exist in graph")

        # run delete node callbacks
        cancel = False
        for fn in list(self._db._on_delete_node.values()):
            if fn(self) is False:
                cancel = True
        if cancel or not self._is_member():
            return False

        # notify delete edge callbacks, for outgoing and incoming edges
        doomed = list(self._edges.values())
        for node in list(graph.values()):
            if node is not self and self._id in node._edges:
                doomed.append(node._edges[self._id])
        for edge in doomed:
            for fn in list(self._db._on_delete_edge.values()):
                fn(edge)

        # Scan again when removing, as callbacks may have added edges.
        if not self._is_member():
            return False
        logger.debug("delete node '%s'", self._id)
        for node in graph.values():
            node._edges.pop(self._id, None)
        self._edges.clear()
        del graph[self._id]
        return True

    @GraphModifyLock
    def set_property(self, key, value):
        """Set a node property."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        self._properties[key] = value

    @GraphModifyLock
    def set_properties(self, properties):
        """Set multiple properties from the provided dict. Properties not in the dict are not removed."""
        _validate_properties(properties)
        self._properties = {**self._properties, **properties}

    def get_property(self, key):
        """Get the property value."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        return self._properties.get(key)

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
        return self._properties.pop(key, None)

    # Returns a list of edges
    def get_edges(self, filter_fn=lambda edge: True):
        """Return all edges, or edges which match the optional filter function."""
        if not callable(filter_fn):
            raise RuntimeError("Filter must be a function.")
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not exist in graph")
        return [edge for edge in list(self._edges.values()) if filter_fn(edge)]

    # Returns an edge to the specified node
    def get_edge(self, destination):
        """Return the edge to the specified destination node, or None if one does not exist."""
        if not isinstance(destination, GraphNode):
            raise RuntimeError("Destination must be an instance of GraphNode.")
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not exist in graph")
        return self._edges.get(destination.get_id())

    # Returns an edge to the specified node
    def has_edge(self, destination):
        """Boolean whether an edge exists to the specified destination node."""
        if not isinstance(destination, GraphNode):
            raise RuntimeError("Destination must be an instance of GraphNode.")
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not exist in graph")
        return destination.get_id() in self._edges

    def _find_route(self, destination_id, skip_ids):
        """Breadth first search for the shortest (fewest edges) route to the
        node with the provided id, avoiding the provided node ids. Callers
        must hold the read lock."""
        graph = self._db._graph
        if self._id not in graph:
            raise RuntimeError("Node does not exist in graph")
        if destination_id == self._id:
            return [self]

        previous = {self._id: None}
        q = deque([self._id])
        found = False
        while q and not found:
            node_id = q.popleft()
            for next_id in list(graph[node_id]._edges):
                if next_id in previous or next_id in skip_ids:
                    continue
                if next_id not in graph:
                    # dangling edge, as may exist in files from older versions
                    continue
                previous[next_id] = node_id
                if next_id == destination_id:
                    found = True
                    break
                q.append(next_id)
        if not found:
            return None

        route = []
        node_id = destination_id
        while node_id != self._id:
            route.append(graph[node_id])
            node_id = previous[node_id]
        route.append(self)
        route.reverse()
        return route

    # Returns a collection of less-optimal routes. The number of
    # these returned depends on the effort to find them, provided
    # as a numeric parameter.
    @GraphReadLock
    def find_routes_to(self, destination, effort=5):
        """Find multiple routes to the destination node, the shortest first,
        returned as a list of routes. Alternatives are found by repeating
        the search while avoiding up to `effort` of the intermediate nodes
        of the routes already found, so the cost grows quickly with effort
        on densely connected graphs."""
        if not isinstance(destination, GraphNode):
            raise RuntimeError("Destination must be an instance of GraphNode.")
        destination_id = destination.get_id()
        q = deque([()])
        searched = {frozenset()}
        routes = []
        found = set()
        while q:
            skip = q.popleft()
            if len(skip) > effort:
                continue
            route = self._find_route(destination_id, set(skip))
            if route:
                for step in route[1:-1]:
                    step_id = step.get_id()
                    if (
                        step_id != self._id
                        and step_id != destination_id
                        and step_id not in skip
                    ):
                        # the route found depends only on which nodes are
                        # skipped, not the order they were chosen in
                        next_skip = skip + (step_id,)
                        key = frozenset(next_skip)
                        if key not in searched:
                            searched.add(key)
                            q.append(next_skip)
                key = tuple(step.get_id() for step in route)
                if key not in found:
                    found.add(key)
                    routes.append(route)

        return routes

    @GraphReadLock
    def find_route_to(self, destination, skip=None):
        """Find a route across the graph from the current node to the
        destination node, returned as an array of nodes. If no route
        exists, returns None. Nodes in the optional skip collection
        are not travelled through."""

        if not isinstance(destination, GraphNode):
            raise RuntimeError("Destination must be an instance of GraphNode.")
        skip_ids = {node.get_id() for node in skip or () if isinstance(node, GraphNode)}
        return self._find_route(destination.get_id(), skip_ids)

    @GraphReadLock
    def find_neighbors(self, distance=1, distance_fn=lambda edge: 1):
        """Find all neighbors within the specified distance, nearest first.
        The distance of an edge is 1 unless a distance function is provided,
        which is called with an edge and must return a non-negative number."""

        if not callable(distance_fn):
            raise RuntimeError("Distance function must be a function.")
        if not isinstance(distance, numbers.Real):
            raise RuntimeError("Distance must be a number.")
        graph = self._db._graph
        if self._id not in graph:
            raise RuntimeError("Node does not exist in graph")

        # Dijkstra's algorithm. The counter keeps nodes at the same distance
        # in the order in which they were discovered.
        best = {self._id: 0}
        done = set()
        neighbors = []
        counter = 0
        heap = [(0, counter, self._id)]
        while heap:
            node_distance, _, node_id = heapq.heappop(heap)
            if node_id in done:
                continue
            done.add(node_id)
            if node_id != self._id:
                neighbors.append(graph[node_id])
            for next_id, edge in list(graph[node_id]._edges.items()):
                if next_id in done or next_id not in graph:
                    # already settled, or a dangling edge
                    continue
                edge_distance = distance_fn(edge)
                if not isinstance(edge_distance, numbers.Real) or math.isnan(
                    edge_distance
                ):
                    raise RuntimeError("Edge distance must be a number.")
                if edge_distance < 0:
                    raise RuntimeError("Edge distance must not be negative.")
                next_distance = node_distance + edge_distance
                if next_distance <= distance and (
                    next_id not in best or next_distance < best[next_id]
                ):
                    best[next_id] = next_distance
                    counter += 1
                    heapq.heappush(heap, (next_distance, counter, next_id))

        return neighbors
