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

    def get_id(self):
        return self._id

    @GraphModifyLock
    def attach(self, destination, properties={}, directed=False):
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
        if destination is not None and type(destination) is not GraphNode:
            raise RuntimeError("Destination must be an instance of GraphNode.")
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        if destination:
            was_connected = destination.get_id() in self._edges
            if was_connected:
                logger.info("detach '%s' from '%s'", self._id, destination.get_id())
                del self._edges[destination.get_id()]
            if not directed:
                del self._db._graph[destination.get_id()]._edges[self._id]
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
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        self.detach()
        del self._db._graph[self._id]

    @GraphModifyLock
    def set_property(self, key, value):
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        self._properties[key] = value

    def get_property(self, key):
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        return self._properties[key] if self.has_property(key) else None

    def get_properties(self):
        return self._properties.copy()

    def has_property(self, key):
        return key in self._properties

    @GraphModifyLock
    def delete_property(self, key):
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        value = self.get_property(key)
        if self.has_property(key):
            del self._properties[key]
        return value

    # Returns a list of edges
    def get_edges(self, criteria=lambda edge: True):
        if type(criteria) is not types.FunctionType:
            raise RuntimeError("Criteria must be a function.")
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        return [edge for edge in self._edges.values() if criteria(edge)]

    # Returns an edge to the specified node
    def get_edge(self, destination):
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
                for step in route:
                    if not step == self._id and not step == destination.get_id():
                        q.append(skip + [step])
                routes.append(route)

        deduped_routes = []
        [deduped_routes.append(x) for x in routes if x not in deduped_routes]
        return deduped_routes

    # Based on code by Eryk Kopczyński
    # https://www.python.org/doc/essays/graphs/
    def find_route_to(self, destination, skip=[]):
        if type(destination) is not GraphNode:
            raise RuntimeError("Destination must be an instance of GraphNode.")
        dist = {self._id: [self]}
        q = deque([self])
        while len(q):
            node = q.popleft()
            for edge in node.get_edges():
                next_node = edge.get_destination()
                if (
                    next_node.get_id() not in dist
                    and destination.get_id() not in dist
                    and not next_node.get_id() in skip
                ):
                    dist[next_node.get_id()] = [
                        dist[node.get_id()],
                        edge.get_destination(),
                    ]
                    q.append(edge.get_destination())

        def flatten(route):
            return route if len(route) == 1 else flatten(route[0]) + [route[1]]

        return (
            flatten(dist.get(destination.get_id()))
            if dist.get(destination.get_id())
            else None
        )
