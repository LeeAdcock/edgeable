<img src="https://raw.githubusercontent.com/LeeAdcock/edgeable/master/assets/logo.png" alt="Edgeable" width="300"/>

*Edgeable is an easy to use, in memory, peristable graph database. It is perfect for prototyping, exploring, and quick implementation in Python applications.* The library is written completely in Python, supporting 3.6+ and Pypy. 

In Edgeable, graphs are made of nodes with a string or numeric identifier and can have any number of properties. Nodes are connected by directed or non-directed edges that can also have any number of properties. Additional convenience capabilities, like route detection through the graph, are built-in. Edgeable is thread safe for multi-threaded applications and easily handles databases with tens to hundreds of thousands of nodes.

## Installation

The Edgeable database library can easily be installed with pip using `pip install edgeable`.

## Examples

### Create a graph instances and add nodes and edges

```
from edgeable import GraphDatabase

graph = new GraphDatabase()
A = graph.put_node('A', {'type': 'building'})
B = graph.put_node('B', {'type': 'classroom'})
A.attach(B, {'relationship': 'contains'})
```

### Loading from a csv file of edges

```
from edgeable import GraphDatabase
import csv

graph = GraphDatabase()
with open('edges.csv') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        node_a = graph.put_node(row[0].strip())
        node_b = graph.put_node(row[1].strip())
        node_1.attach(node_b)
```

### Write a csv file of edges

```
with open('edges.csv', 'w') as csvfile:
    writer = csv.writer(csvfile)
    for node in graph.get_nodes():
        for edge in node.get_edges():
            writer.writerow([
                edge.get_source().get_id(), 
                edge.get_destination().get_id()
            ])
```

## Classes

### Graph Class
The `GraphDatabase` class represents the entire graph. Instances of `GraphDatabase` provide the ability to retrieve and creates nodes, as well as save or load from the file system.

##### Graph Constructor
The `GraphDatabase()` constructor is used to create a new graph database instance.  

The `with` syntax can be used to initialize the graph and ensure it saved once the block is exicted.

```
from edgeable import GraphDatabase

with new GraphDatabase(filename="mygraph.db") as graph:
    A = graph.put_node('A', {'type': 'building'})
    B = graph.put_node('B', {'type': 'classroom'})
    A.attach(B, {'relationship': 'contains'})
```

##### Graph Persistance
- `load(filename="graph.db")` - Load the database from the file system. Optionally takes a custom filename.
- `save(filename="graph.db")` - Save the database to the file system. Optionally takes a custom filename.

##### Graph Nodes and Edges

- `put_node(id, properties={})` - Creates or retrieves the instance of `GraphNode` with the provided identifier. The optionally provided properties are set or updated on the node.
- `has_node(id)` - Taking a node identifier, return an instance of type `GraphNode`.
- `get_node(id)` - Taking a node identifier, return an instance of type `GraphNode` if it exists in the database. Returns `None` otherwise.
- `get_nodes(criteria=lambda node: True)` - Retrieve a list of `GraphNode` instances from the database. If the optional criteria is not provided, all nodes are returned, otherwise the criteria function is used to return only matching nodes.
- `get_node_count()` - Return the number of nodes in the database.
- `get_edge_count()` - Return the number of edges in the database.

##### Graph Properties
- `set_property(key, value)` - Set a property on the node with the provided key and value.
- `set_properties(properties)` - Provide a dict to set multiple properites on the database.
- `get_property(key)` - Retrieve the node's property value for the provided key.
- `get_properties()` - Retrieve a `dict` containing all properties set on the node.
- `has_property(key)` - Returns a boolean indicating whether the property key is defined.
- `delete_property(key)` - Removes a property.

### Node Class
The `GraphNode` class represent nodes and associated properties within the graph. Nodes can be connected through directed or non-directed edges.

- `delete()` - Delete the node from the database, removing any associated edges.

##### Node Edges
- `attach(destination, properties={}, directed=False)` - Attach the current node to the destination node with a new edge. The optionally provided properties will be set on the edge, whether it exists or is created new. The releationship will be nondirectional unless `directed` is set to `True`. The method returns a boolean indicating if a new edge was created between the nodes.
- `detach(destination=None, directed=False)` - Detach the current node from the destination node, removing any connecting edge. If no destination is provided, all attached nodes are detached. If `directed` is set to `True`, then the edge is only removed in the current direction, any edge in the other directions is untouched. The method returns a boolean indicating if any edges were removed.
- `get_edges(criteria=lambda edge: True)` - Retrieve a list of `GraphEdge` instances from the database. If the optional criteria is not provided, all edges for the node are returned, otherwise the criteria function is used to return only matching edges.
- `get_edge(destination)` - Retrieve the edge that leads from the current node to the provided destination node.
- `has_edge(destination)` - Returns a boolean indicating whether there is an edge from the current node to the destination node.

##### Node Properties
- `set_property(key, value)` - Set a property on the node with the provided key and value.
- `set_properties(properties)` - Provide a dict to set multiple properites on the node.
- `get_property(key)` - Retrieve the node's property value for the provided key.
- `get_properties()` - Retrieve a `dict` containing all properties set on the node.
- `has_property(key)` - Returns a boolean indicating whether the property key is defined.
- `delete_property(key)` - Removes a property.

##### Node Routes
- `find_routes_to(end, effort=5)`
- `find_route_to(end, skip=[])`

### Edge Class
The `GraphEdge` class representes the connections between `GraphNode` instances in the database. All methods assume edges are nondirected, so interactions with edges equally manipulates an edge in each direction between nodes.  This behavior can be overridden for specific calls, resulting in the creation, modification, or deletion of directional edges.

- `get_destination()` - Retrieve the `GraphNode` instance that is the destination of this edge.
- `get_source()` - Retrieve the `GraphNode` instance that is the source of this edge.
- `delete(directed=False)` - Delete the edge from the database. If `directed` is `True` than only the edge in this direction is deleted.

##### Edge Properties
- `set_property(key, value, directed=False)` - Set a property on the node with the provided key and value. If `directed` is `True` than the property is set only on the edge in this direction.
- `set_properties(properties, directed=False)` - Provide a dict to set multiple properites on the edge.
- `get_property(key)` - Retrieve the node's property value for the provided key.
- `get_properties()` - Retrieve a `dict` containing all properties set on the edge.
- `has_property(key)` - Returns a boolean indicating whether the property key is defined.
- `delete_property(key)` - Removes a property.

## Resources

Build process: https://app.travis-ci.com/github/LeeAdcock/edgeable

PyPi: https://pypi.org/project/edgeable/