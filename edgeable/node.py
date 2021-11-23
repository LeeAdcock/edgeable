from edgeable import GraphEdge
from collections import deque
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edgeable")


class GraphNode:
    def __init__(self, db, id):
        self.db = db
        self.id = id

    def __eq__(self, other):
        if isinstance(other, GraphNode):
            return self.get_id() == other.get_id()
        return False

    def __str__(self):
        return self.get_id()

    def __repr__(self):
        return self.get_id()

    def get_id(self):
        return self.id

    def attach(self, destination, properties={}, directed=False):
        if self.id not in self.db.graph:
            raise RuntimeError("Node does not existing in graph")
        if destination.get_id() == self.id:
            return False
        is_connected = destination.get_id() in self.db.graph[self.id]["connections"]
        if not is_connected:
            logger.info(
                "attach '%s' -> '%s' (%s)", self.id, destination.get_id(), properties
            )
            self.db.graph[self.id]["connections"][
                destination.get_id()
            ] = properties.copy()
            if not directed:
                self.db.graph[destination.get_id()]["connections"][
                    self.id
                ] = properties.copy()
        else:
            self.db.graph[self.id]["connections"][destination.get_id()] = {
                **self.db.graph[self.id]["connections"][destination.get_id()],
                **properties,
            }

        return not is_connected

    def detach(self, destination=None, directed=False):
        if self.id not in self.db.graph:
            raise RuntimeError("Node does not existing in graph")
        if destination:
            was_connected = (
                destination.get_id() in self.db.graph[self.id]["connections"]
            )
            if was_connected:
                logger.info("detach '%s' from '%s'", self.id, destination.get_id())
                del self.db.graph[self.id]["connections"][destination.get_id()]
            if not directed:
                del self.db.graph[destination.get_id()]["connections"][self.id]
            return was_connected
        else:
            was_connected = False
            for edge in self.get_edges():
                was_connected = was_connected or self.detach(edge.get_destination(), directed=directed)
        return was_connected

    def delete(self):
        if self.id not in self.db.graph:
            raise RuntimeError("Node does not existing in graph")
        self.detach()
        del self.db.graph[self.id]

    def set_property(self, key, value):
        if self.id not in self.db.graph:
            raise RuntimeError("Node does not existing in graph")
        self.db.graph[self.id]["meta"][key] = value

    def get_property(self, key):
        if self.id not in self.db.graph:
            raise RuntimeError("Node does not existing in graph")
        return (
            self.db.graph[self.id]["meta"][key]
            if key in self.db.graph[self.id]["meta"]
            else None
        )

    def get_properties(self):
        return self.db.graph[self.id]["meta"].copy() if self.id in self.db.graph else {}

    # Returns a list of edges
    def get_edges(self, criteria=lambda edge: True):
        if self.id not in self.db.graph:
            raise RuntimeError("Node does not existing in graph")
        return [
            edge
            for edge in [
                GraphEdge(
                    destination=GraphNode(self.db, id),
                    source=self,
                )
                for id in self.db.graph[self.id]["connections"]
            ]
            if criteria(edge)
        ]

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
                    if not step == self.id and not step == end.get_id():
                        q.append(skip + [step])
                routes.append(route)

        deduped_routes = []
        [deduped_routes.append(x) for x in routes if x not in deduped_routes]
        return deduped_routes

    # Based on code by Eryk Kopczyński
    # https://www.python.org/doc/essays/graphs/
    def find_route_to(self, end, skip=[]):
        dist = {self.id: [self]}
        q = deque([self])
        while len(q):
            node = q.popleft()
            for edge in node.get_edges():
                destination_id = edge.get_destination().get_id()
                if destination_id not in dist and not destination_id in skip:
                    dist[destination_id] = [dist[node.get_id()], edge.get_destination()]
                    q.append(edge.get_destination())

        def flatten(route):
            return route if len(route) == 1 else flatten(route[0]) + [route[1]]

        return flatten(dist.get(end.get_id())) if dist.get(end.get_id()) else None
