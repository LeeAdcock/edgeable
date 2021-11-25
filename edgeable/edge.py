from edgeable import GraphModifyLock


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

    @GraphModifyLock
    def set_property(self, key, value, directed=False):
        if type(key) is not str:
            raise RuntimeError("Key must be a string")
        self._properties[key] = value

        if not directed:
            self._db._graph[self._destination_id]._edges[self._source_id]._properties[
                key
            ] = value

    @GraphModifyLock
    def set_properties(self, properties, directed=False):
        if type(properties) is not dict:
            raise RuntimeError("Key properties be a dict.")
        self._properties = {**self._properties, **properties}
        if not directed:
            destination = self._db._graph[self._destination_id]
            destination._edges[self._source_id]._properties = {
                **destination._edges[self._source_id]._properties,
                **properties,
            }

    def get_property(self, key):
        if type(key) is not str:
            raise RuntimeError("Key must be a string")
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

    @GraphModifyLock
    def delete(self, directed=False):
        self._db._graph[self._source_id].detach(
            self._db._graph[self._destination_id], directed=directed
        )
