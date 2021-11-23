class GraphEdge:
    def __init__(self, db, destination, source, properties):
        self._db = db
        self._destination_id = destination.get_id()
        self._source_id = source.get_id()

        self._properties = properties.copy()

    def __eq__(self, other):
        if isinstance(other, GraphEdge):
            return (
                self._source_id == other.source.get_id()
                and self._destination_id == other.destination.get_id()
            )
        return False

    def __str__(self):
        return self._source_id + "->" + self._destination_id

    def __repr__(self):
        return self._source_id + "->" + self._destination_id

    def get_destination(self):
        return self._db._graph[self._destination_id]

    def get_source(self):
        return self._db._graph[self._source_id]

    def set_property(self, key, value, directed=False):
        if type(key) is not str:
            raise RuntimeError("Key must be a string")
        self._properties[key] = value

        if not directed:
            self._db._graph[self._destination_id]._edges[self._source_id]._properties[
                key
            ] = value

    def get_property(self, key):
        if type(key) is not str:
            raise RuntimeError("Key must be a string")
        return self._properties[key] if key in self._properties else None

    def get_properties(self):
        return self._properties.copy()

    def delete(self, directed=False):
        self._db._graph[self._source_id].detach(
            self._db._graph[self._destination_id], directed=directed
        )
