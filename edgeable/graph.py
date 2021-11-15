import pickle
from collections import deque
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("graphdb")


class GraphEdge:
    def __init__(self, destination, source):
        self.destination = destination
        self.source = source

    def get_destination(self):
        return self.destination

    def get_source(self):
        return self.source

    def set_property(self, key, value):
        db = self.source.db
        meta = db.graph[self.source.get_id()]["connections"][self.destination.get_id()]
        meta[key] = value

    def get_property(self, key):
        db = self.source.db
        meta = db.graph[self.source.get_id()]["connections"][self.destination.get_id()]
        return meta[key] if key in meta else None

    def get_properties(self):
        db = self.source.db
        meta = db.graph[self.source.get_id()]["connections"][self.destination.get_id()]
        return meta.copy()


class GraphNode:
    def __init__(self, db, id):
        self.db = db
        self.id = id

    def get_id(self):
        return self.id

    def attach(self, destination, properties={}):
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
            self.db.graph[destination.get_id()]["connections"][
                self.id
            ] = properties.copy()

        return not is_connected

    def detach(self, destination=None):
        if destination:
            was_connected = (
                destination.get_id() in self.db.graph[self.id]["connections"]
            )
            if was_connected:
                logger.info("detach '%s' from '%s'", self.id, destination.get_id())
                del self.db.graph[self.id]["connections"][destination.get_id()]
                del self.db.graph[destination.get_id()]["connections"][self.id]
            return was_connected
        else:
            for edge in self.get_edges():
                self.detach(edge.get_destination())

    def set_property(self, key, value):
        self.db.graph[self.id]["meta"][key] = value

    def get_property(self, key):
        return (
            self.db.graph[self.id]["meta"][key]
            if key in self.db.graph[self.id]["meta"]
            else None
        )

    def get_properties(self):
        return self.db.graph[self.id]["meta"].copy()

    # Returns a list of edges
    def get_edges(self):
        return [
            GraphEdge(
                destination=GraphNode(self.db, id),
                source=self,
            )
            for id in self.db.graph[self.id]["connections"]
        ]

    # Returns an edge to the specified node
    # TODO should this return an array?
    def get_edge(self, id):
        edges = [
            edge for edge in self.get_edges() if edge.get_destination().get_id() == id
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
        dist = {self.id: [self.id]}
        q = deque([self])
        while len(q):
            node = q.popleft()
            for edge in node.get_edges():
                destination_id = edge.get_destination().get_id()
                if destination_id not in dist and not destination_id in skip:
                    dist[destination_id] = [dist[node.get_id()], destination_id]
                    q.append(edge.get_destination())

        def flatten(route):
            return route if len(route) == 1 else flatten(route[0]) + [route[1]]

        return flatten(dist.get(end.get_id())) if dist.get(end.get_id()) else None


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
    def get_node(self, id):
        if not isinstance(id, str):
            raise "Node id must be a string."

        if id not in self.graph:
            logger.info("create node '%s'", id)
            self.graph[id] = {"connections": {}, "meta": {}}

        return GraphNode(self, id)

    def get_node_count(self):
        return len(self.graph)

    def get_edge_count(self):
        return sum([len(self.graph[node]) for node in self.graph])

    def load(self):
        try:
            with open(self.filename, "rb") as f:
                self.graph = pickle.load(f)
        except:
            pass

    def save(self):
        with open(self.filename, "wb") as f:
            pickle.dump(self.graph, f, protocol=pickle.DEFAULT_PROTOCOL)
