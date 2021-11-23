from edgeable import GraphEdge
from collections import deque
import logging

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

    def attach(self, destination, properties={}, directed=False):
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
                source=self, destination=destination, properties=properties
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

    def detach(self, destination=None, directed=False):
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

    def delete(self):
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        self.detach()
        del self._db._graph[self._id]

    def set_property(self, key, value):
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        self._properties[key] = value

    def get_property(self, key):
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        print(self._properties)
        return self._properties[key] if key in self._properties else None

    def get_properties(self):
        return self._properties.copy() if self._id in self._db._graph else {}

    # Returns a list of edges
    def get_edges(self, criteria=lambda edge: True):
        if self._id not in self._db._graph:
            raise RuntimeError("Node does not existing in graph")
        return [edge for edge in self._edges.values() if criteria(edge)]

    # Returns an edge to the specified node
    def get_edge(self, destination):
        edges = [
            edge
            for edge in self.get_edges()
            if edge.get_destination().get_id() == destination.get_id()
        ]
        if edges:
            return edges[0]

        return None

    # Returns a collection of less-optimal routes. The number of
    # these returned depends on the effort to find them, provided
    # as a numeric parameter.
    def find_routes_to(self, end, effort=5):
        q = deque([[]])
        routes = []
        while len(q):
            skip = q.popleft()
            route = self.find_route_to(end, skip)
            if route and len(skip) <= effort:
                for step in route:
                    if not step == self._id and not step == end.get_id():
                        q.append(skip + [step])
                routes.append(route)

        deduped_routes = []
        [deduped_routes.append(x) for x in routes if x not in deduped_routes]
        return deduped_routes

    # Based on code by Eryk Kopczyński
    # https://www.python.org/doc/essays/graphs/
    def find_route_to(self, end, skip=[]):
        dist = {self._id: [self]}
        q = deque([self])
        while len(q):
            node = q.popleft()
            for edge in node.get_edges():
                destination = edge.get_destination()
                if (
                    destination.get_id() not in dist
                    and end.get_id() not in dist
                    and not destination.get_id() in skip
                ):
                    dist[destination.get_id()] = [
                        dist[node.get_id()],
                        edge.get_destination(),
                    ]
                    q.append(edge.get_destination())

        def flatten(route):
            return route if len(route) == 1 else flatten(route[0]) + [route[1]]

        return flatten(dist.get(end.get_id())) if dist.get(end.get_id()) else None
