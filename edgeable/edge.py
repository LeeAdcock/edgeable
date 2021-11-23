class GraphEdge:
    def __init__(self, destination, source, properties):
        self._destination = destination
        self._source = source

        self._properties = properties.copy()

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
        self._properties[key] = value

        if not directed:
            db = self._source._db
            db._graph[self._destination.get_id()]._edges[
                self._source.get_id()
            ]._properties[key] = value

    def get_property(self, key):
        return self._properties[key] if key in self._properties else None

    def get_properties(self):
        return self._properties.copy()

    def delete(self, directed=False):
        self._source.detach(self._destination, directed=directed)
