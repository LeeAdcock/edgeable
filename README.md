# Edgeable

*Edgeable was designed as an easy to use, in memory, peristable graph database. It is perfect for prototyping, exploring, and quick implementation in Python applications.* Nodes have one string identifier and an unlimited number of key:value properties. They are connected by directed or non-directed (default) edges. These edges can also have an unlimited number of key:value properties. Additional convenience capabilities, like route detection through the graph are built-in.

## Installation

The Edgeable database library can easily be installed with pip using `pip install edgeable`.

## Example

```
from edgeable import GraphDatabase

db = new GraphDatabase()
A = db.put_node('A', {'type': 'building'})
B = db.put_node('B', {'type': 'classroom'})
A.attach(B, {'relationship': 'contains'})
```

## Classes

### Database Class
The `GraphDatabase` class represents the entire graph. Instances of `GraphDatabase` provide the ability to retrieve and creates nodes, as well as save or load from the file system.

##### Constructor
The `GraphDatabase(filename="graph.db")` constructor is used to create a graph database instance.  It optionally takes a filename to use when saving or loading the database to the file system.

##### Persistance
- `load()` - Load the database from the file system.
- `save()` - Save the database to the file system.

##### Nodes and Edges

- `get_node_count()` - Return the number of nodes in the database.
- `get_edge_count()` - Return the number of edges in the database.
- `has_node(id)` - Taking a node identifier, return an instance of type `GraphNode`.
- `get_node(id, properties={})` - Retrieve the instance of `GraphNode` with the provided identifier. If one does not exist, the node is created. Regardless, the optionally provided properties are set on the node.
- `get_nodes(criteria=lambda node: True)` - Retrieve a list of `GraphNode` instances from the database. If the optional criteria is not provided, all nodes are returned, otherwise the criteria function is used to return only matching nodes.

### Node Class
The `GraphNode` class represent nodes and associated properties within the graph. Nodes can be connected through directed or non-directed edges.

- `delete()` - Delete the node from the database, removing any associated edges.

##### Edges
- `attach(destination, properties={}, directed=False)` - Attach the current node to the destination node with a new edge. The optionally provided properties will be set on the edge, whether it exists or is created new. The releationship will be nondirectional unless `directed` is set to `True`. The method returns a boolean indicating if a new edge was created between the nodes.
- `detach(destination=None, directed=False)` - Detach the current node from the destination node, removing any connecting edge. If no destination is provided, all attached nodes are detached. If `directed` is set to `True`, then the edge is only removed in the current direction, any edge in the other directions is untouched. The method returns a boolean indicating if any edges were removed.
- `get_edges(criteria=lambda edge: True)` - Retrieve a list of `GraphEdge` instances from the database. If the optional criteria is not provided, all edges for the node are returned, otherwise the criteria function is used to return only matching edges.
- `get_edge(destination)` - Retrieve the edge that leads from the current node to the provided destination node.

##### Properties
- `set_property(key, value)` - Set a property on the node with the provided key and value.
- `get_property(key)` - Retrieve the node's property value for the provided key.
- `get_properties()` - Retrieve a `dict` containing all properties set on the node.

##### Routes
- `find_routes_to(end, effort=5)`
- `find_route_to(end, skip=[])`

### Edge Class
The `GraphEdge` class representes the connections between `GraphNode` instances in the database. All methods assume edges are nondirected, so interactions with edges equally manipulates an edge in each direction between nodes.  This behavior can be overridden for specific calls, resulting in the creation, modification, or deletion of directional edges.

- `get_destination()` - Retrieve the `GraphNode` instance that is the destination of this edge.
- `get_source()` - Retrieve the `GraphNode` instance that is the source of this edge.
- `delete(directed=False)` - Delete the edge from the database. If `directed` is `True` than only the edge in this direction is deleted.

##### Properties
- `set_property(key, value, directed=False)` - Set a property on the node with the provided key and value. If `directed` is `True` than the property is set only on the edge in this direction.
- `get_property(key)` - Retrieve the node's property value for the provided key.
- `get_properties()` - Retrieve a `dict` containing all properties set on the edge.

## Resources

Build process: https://app.travis-ci.com/github/LeeAdcock/edgeable
PyPi: https://pypi.org/project/edgeable/