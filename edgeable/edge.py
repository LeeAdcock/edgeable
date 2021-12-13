from edgeable import GraphModifyLock


class GraphEdge:
    """Class representing edges between nodes in the graph."""

    def __init__(self, db, destination, source, properties):
        self._db = db
        self._destination_id = destination.get_id()
        self._source_id = source.get_id()

        self._properties = properties.copy()

    def __eq__(self, other):
        if isinstance(other, GraphEdge):
            return (
                self._source_id == other._source_id
                and self._destination_id == other._destination_id
            )
        return False

    def __str__(self):
        return self._source_id + "->" + self._destination_id

    def __repr__(self):
        return self._source_id + "->" + self._destination_id

    def get_destination(self):
        """Get the node which is the destination of this edge."""
        return self._db._graph[self._destination_id]

    def get_source(self):
        """Get the node which is the source of this edge."""
        return self._db._graph[self._source_id]

    @GraphModifyLock
    def set_property(self, key, value, directed=False):
        """Set an edge property. If directed=False the property is mirrored
        to an edge in the reverse direction."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string")
        self._properties[key] = value

        if not directed:
            if (
                self._destination_id in self._db._graph
                and self._source_id in self._db._graph[self._destination_id]._edges
            ):
                self._db._graph[self._destination_id]._edges[
                    self._source_id
                ]._properties[key] = value

    @GraphModifyLock
    def set_properties(self, properties, directed=False):
        """Set multiple properties from the provided dict. Properties not in the dict
        are not removed. If directed=False the property is mirrored
        to an edge in the reverse direction."""
        if type(properties) is not dict:
            raise RuntimeError("Key properties be a dict.")
        self._properties = {**self._properties, **properties}
        if not directed:
            if (
                self._destination_id in self._db._graph
                and self._source_id in self._db._graph[self._destination_id]._edges
            ):
                destination = self._db._graph[self._destination_id]
                destination._edges[self._source_id]._properties = {
                    **destination._edges[self._source_id]._properties,
                    **properties,
                }

    def get_property(self, key):
        """Get the property value."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string")
        return self._properties[key] if self.has_property(key) else None

    def get_properties(self):
        """Get a dict containing all properties and values."""
        return self._properties.copy()

    def has_property(self, key):
        """Boolean value indicating if the property is defined."""
        return key in self._properties

    @GraphModifyLock
    def delete_property(self, key):
        """Delete a property if it is defined. Returns the previous value, or None."""
        if type(key) is not str:
            raise RuntimeError("Key must be a string.")
        value = self.get_property(key)
        if self.has_property(key):
            del self._properties[key]
        return value

    @GraphModifyLock
    def delete(self, directed=False):
        """Delete this edge between nodes. If directed=False than any edge in
        the reverse direction is also deleted."""
        self._db._graph[self._source_id].detach(
            self._db._graph[self._destination_id], directed=directed
        )
