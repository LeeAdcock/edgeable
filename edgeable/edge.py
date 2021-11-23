class GraphEdge:
    def __init__(self, destination, source):
        self._destination = destination
        self._source = source

    def __eq__(self, other):
        if isinstance(other, GraphEdge):
            return (
                self._source.get_id() == other.source.get_id()
                and self._destination.get_id() == other.destination.get_id()
            )
        return False

    def __str__(self):
        return self._source.get_id() + "->" + self._destination.get_id()

    def __repr__(self):
        return self._source.get_id() + "->" + self._destination.get_id()

    def get_destination(self):
        return self._destination

    def get_source(self):
        return self._source

    def set_property(self, key, value, directed=False):
        db = self._source._db
        meta = db._graph[self._source.get_id()]["connections"][self._destination.get_id()]
        meta[key] = value

        if not directed:
            meta = db._graph[self._destination.get_id()]["connections"][
                self._source.get_id()
            ]
            meta[key] = value

    def get_property(self, key):
        db = self._source._db
        meta = db._graph[self._source.get_id()]["connections"][self._destination.get_id()]
        return meta[key] if key in meta else None

    def get_properties(self):
        db = self._source._db
        meta = db._graph[self._source.get_id()]["connections"][self._destination.get_id()]
        return meta.copy()

    def delete(self, directed=False):
        self._source.detach(self._destination, directed=directed)
