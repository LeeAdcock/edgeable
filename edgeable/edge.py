class GraphEdge:
    def __init__(self, destination, source):
        self.destination = destination
        self.source = source

    def __eq__(self, other):
        if isinstance(other, GraphEdge):
            return (
                self.source.get_id() == other.source.get_id()
                and self.destination.get_id() == other.destination.get_id()
            )
        return False

    def __str__(self):
        return self.source.get_id() + "->" + self.destination.get_id()

    def __repr__(self):
        return self.source.get_id() + "->" + self.destination.get_id()

    def get_destination(self):
        return self.destination

    def get_source(self):
        return self.source

    def set_property(self, key, value, directed=False):
        db = self.source.db
        meta = db.graph[self.source.get_id()]["connections"][self.destination.get_id()]
        meta[key] = value

        if not directed:
            meta = db.graph[self.destination.get_id()]["connections"][
                self.source.get_id()
            ]
            meta[key] = value

    def get_property(self, key):
        db = self.source.db
        meta = db.graph[self.source.get_id()]["connections"][self.destination.get_id()]
        return meta[key] if key in meta else None

    def get_properties(self):
        db = self.source.db
        meta = db.graph[self.source.get_id()]["connections"][self.destination.get_id()]
        return meta.copy()

    def delete(self, directed=False):
        self.source.detach(self.destination, directed=directed)
