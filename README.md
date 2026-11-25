<img src="https://raw.githubusercontent.com/LeeAdcock/edgeable/master/assets/logo.png" alt="Edgeable" width="300"/>

[![CI](https://github.com/LeeAdcock/edgeable/actions/workflows/ci.yml/badge.svg)](https://github.com/LeeAdcock/edgeable/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/edgeable)](https://pypi.org/project/edgeable/)
[![Python versions](https://img.shields.io/pypi/pyversions/edgeable)](https://pypi.org/project/edgeable/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/LeeAdcock/edgeable/blob/master/LICENSE)

*Edgeable is an easy to use, in memory, persistable graph database. It is perfect for prototyping, exploring, and quick implementation in Python applications.*

- Nodes and edges, each with any number of properties.
- Directed and undirected edges.
- Shortest route and neighbor search built in.
- Saves to a single file; reloads with one line.
- Thread safe.
- Pure Python, no dependencies. Requires Python 3.10 or newer.

## Contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Concepts](#concepts)
- [More examples](#more-examples)
- [API reference](#api-reference)
- [Persistence and file safety](#persistence-and-file-safety)
- [Threads and performance](#threads-and-performance)
- [Logging](#logging)
- [Upgrading from 0.1](#upgrading-from-01)
- [Development](#development)
- [Resources](#resources)

## Installation

```
pip install edgeable
```

## Quick start

```python
from edgeable import GraphDatabase

# Opens campus.db if it exists, otherwise starts empty.
# Leaving the "with" block saves the graph to that file.
with GraphDatabase(filename="campus.db") as graph:
    # Create nodes. The second argument is an optional dict of properties.
    library = graph.put_node("library", {"type": "building"})
    hall = graph.put_node("hall", {"type": "building"})
    room = graph.put_node("room-101", {"type": "classroom"})

    # Connect them. Edges are undirected unless you ask otherwise.
    library.attach(hall, {"walk_minutes": 4})
    hall.attach(room, {"walk_minutes": 1})

    # Look things up.
    buildings = graph.get_nodes(lambda node: node.get_property("type") == "building")
    print(buildings)  # [library, hall]

    # Find a route and nearby nodes.
    print(library.find_route_to(room))  # [library, hall, room-101]
    print(library.find_neighbors(distance=1))  # [hall]
```

The next time the program runs, `GraphDatabase(filename="campus.db")` loads the saved graph.

## Concepts

### Nodes

A node has an identifier and a dict of properties. `put_node` creates the node, or returns the existing node with that identifier.

Identifiers are strings or numbers. Prefer strings or integers: numbers that compare equal are the same identifier, so `1`, `1.0` and `True` all name one node.

### Edges are stored per direction

An edge leads from a source node to a destination node. An undirected connection is stored as **two edges**, one in each direction.

- `a.attach(b)` creates both `a -> b` and `b -> a`.
- `a.attach(b, directed=True)` creates only `a -> b`.

This has two visible effects:

- `get_edge_count()` and `get_edges()` count each direction, so one undirected connection counts as two edges.
- Each direction has its own properties. Methods that change an edge keep both directions in step unless you pass `directed=True`. The one exception is `delete_property`, which only changes the edge it is called on.

### Properties

The database, every node and every edge each have their own properties. Keys must be strings. `get_property` returns `None` for a key that is not set.

### Node objects can go stale

A `GraphNode` object is only valid while it is the node stored in the graph. After `node.delete()` or `graph.reload()`, node objects you were holding are stale, and calling `attach`, `detach` or `delete` on them raises `RuntimeError`. Fetch the node again with `get_node`.

### Errors

Invalid arguments raise `RuntimeError`, for example a property key that is not a string, or a destination that is not a node in the same graph.

## More examples

The examples below continue from the quick start.

### Directed edges and edge properties

```python
graph = GraphDatabase(filename="campus.db")
library = graph.get_node("library")
hall = graph.get_node("hall")
annex = graph.put_node("annex")

# A one-way connection.
hall.attach(annex, {"walk_minutes": 2}, directed=True)
print(hall.has_edge(annex), annex.has_edge(hall))  # True False

# Read and change the properties of an edge.
edge = library.get_edge(hall)
print(edge.get_property("walk_minutes"))  # 4
edge.set_property("covered", True)  # set on both directions
print(hall.get_edge(library).get_property("covered"))  # True
```

### Weighted neighbors

```python
# Everything within a five minute walk of the library, nearest first.
nearby = library.find_neighbors(
    distance=5,
    distance_fn=lambda edge: edge.get_property("walk_minutes"),
)
print(nearby)  # [hall, room-101]
```

### Routes that avoid a node

```python
room = graph.get_node("room-101")
print(library.find_route_to(room, skip=[hall]))  # None: the only route is through the hall
```

### Callbacks

```python
def no_orphans(node):
    # Returning False cancels the event.
    if node.get_edges():
        print("refusing to delete", node)
        return False


callback_id = graph.on_delete_node(no_orphans)
print(hall.delete())  # prints "refusing to delete hall", then False

graph.on_delete_node(None, id=callback_id)  # remove the callback
```

### Load edges from a CSV file

```python
import csv

with open("edges.csv", "w", newline="") as csvfile:
    csv.writer(csvfile).writerows([["a", "b"], ["b", "c"]])

with open("edges.csv", newline="") as csvfile:
    for source, destination in csv.reader(csvfile):
        graph.put_node(source.strip()).attach(graph.put_node(destination.strip()))
```

### Write edges to a CSV file

An undirected connection is two edges, so it is written as two rows. To write each connection once, skip one of the directions.

```python
with open("edges.csv", "w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    for edge in graph.get_edges():
        source = edge.get_source().get_id()
        destination = edge.get_destination().get_id()
        reverse_exists = edge.get_destination().has_edge(edge.get_source())
        if not reverse_exists or source <= destination:
            writer.writerow([source, destination])
```

## API reference

### GraphDatabase

`GraphDatabase(filename="graph.db", properties=None)`

Creates a database. If `filename` exists it is loaded; otherwise the database starts empty. Nothing is written until `save()` is called.

`properties` is an optional dict of database properties. When a file is loaded, its saved properties are applied first and the ones passed here are set on top.

Used in a `with` statement, the database is saved when the block exits.

#### Saving and loading

| Method | Description |
|---|---|
| `save()` | Write the graph to `filename`. The directory must already exist. |
| `reload()` | Replace the graph and database properties with the contents of the file, discarding unsaved changes. Raises `FileNotFoundError` if the file does not exist. Callbacks stay registered. |

#### Nodes and edges

| Method | Description |
|---|---|
| `put_node(id, properties={})` | Create the node, or update the existing node by merging in `properties`. Returns the `GraphNode`, or `None` if a create callback cancelled it. |
| `get_node(id)` | Return the `GraphNode`, or `None` if it does not exist. |
| `has_node(id)` | Return whether the node exists. |
| `get_nodes(filter_fn=lambda node: True)` | Return a list of all nodes, or those for which `filter_fn(node)` is true. |
| `get_edges(edge_filter_fn=lambda edge: True, node_filter_fn=lambda node: True)` | Return a list of all edges. `edge_filter_fn(edge)` selects edges; `node_filter_fn(node)` selects which source nodes to take edges from. |
| `get_node_count()` | Return the number of nodes. |
| `get_edge_count()` | Return the number of edges, counting each direction. |

Filters can be any callable. Leave a filter out to match everything.

#### Database properties

| Method | Description |
|---|---|
| `set_property(key, value)` | Set one property. |
| `set_properties(properties)` | Set several properties from a dict. Other properties are kept. |
| `get_property(key)` | Return the value, or `None` if it is not set. |
| `get_properties()` | Return a copy of all properties as a dict. |
| `has_property(key)` | Return whether the property is set. |
| `delete_property(key)` | Remove the property. Returns its previous value, or `None`. |

Nodes and edges have the same six property methods.

#### Callbacks

| Method | Called when |
|---|---|
| `on_create_node(fn, id=None)` | A node is about to be created. `fn(node)`. |
| `on_delete_node(fn, id=None)` | A node is about to be deleted. `fn(node)`. |
| `on_create_edge(fn, id=None)` | An edge is about to be created. `fn(edge)`. |
| `on_delete_edge(fn, id=None)` | An edge is about to be deleted. `fn(edge)`. |

- Each call returns the callback's id. Pass your own `id` to choose it.
- Register again with the same `id` to replace a callback. Pass `fn=None` with the `id` to remove it.
- A callback that returns exactly `False` cancels the event. Any other return value, including `None` and `0`, does not.
- Every registered callback is called, even after one has cancelled.
- Edge callbacks are called once per direction. An undirected `attach` or `detach` is all-or-nothing: if either direction is cancelled, neither changes.
- When a node is deleted, `on_delete_edge` callbacks are called for each of its edges but cannot cancel.
- Callbacks may read and change the graph.
- Callbacks are not saved with the database.

### GraphNode

Nodes are created with `GraphDatabase.put_node`, not directly.

| Method | Description |
|---|---|
| `get_id()` | Return the node's identifier. |
| `delete()` | Delete the node and every edge to or from it. Returns `True`, or `False` if a callback cancelled it. |

#### Edges

| Method | Description |
|---|---|
| `attach(destination, properties=None, directed=False)` | Connect this node to `destination`. `properties` are set on the edge whether it is new or already exists. Returns `True` if an edge was created, `False` if nothing new was created or a callback cancelled it. Attaching a node to itself does nothing. |
| `detach(destination=None, directed=False)` | Remove the connection to `destination`, or to every node if no destination is given. With `directed=True` only the edge leading from this node is removed. Returns whether any edge was removed. |
| `get_edges(filter_fn=lambda edge: True)` | Return a list of the edges leading from this node, or those for which `filter_fn(edge)` is true. |
| `get_edge(destination)` | Return the `GraphEdge` leading to `destination`, or `None`. |
| `has_edge(destination)` | Return whether an edge leads to `destination`. |

#### Routes and neighbors

| Method | Description |
|---|---|
| `find_route_to(destination, skip=None)` | Return a shortest route, by number of edges, as a list of nodes from this node to `destination`. Returns `None` if there is no route. Nodes in the optional `skip` list are not travelled through. |
| `find_routes_to(destination, effort=5)` | Return a list of alternative routes, shortest first. After the shortest route, the search repeats while avoiding nodes used by routes already found. `effort` is the most nodes that may be avoided at once: higher values find more, less direct routes and take longer. |
| `find_neighbors(distance=1, distance_fn=lambda edge: 1)` | Return a list of the nodes within `distance` of this node, nearest first, not including this node. Each edge counts as 1 unless `distance_fn(edge)` returns another non-negative number. |

Routes follow edge directions.

### GraphEdge

Edges are created with `GraphNode.attach`, not directly.

| Method | Description |
|---|---|
| `get_source()` | Return the node this edge leads from. |
| `get_destination()` | Return the node this edge leads to. |
| `delete(directed=False)` | Delete the edge. The reverse edge is also deleted unless `directed=True`. Returns whether an edge was removed. |
| `set_property(key, value, directed=False)` | Set a property. It is also set on the reverse edge, if there is one, unless `directed=True`. |
| `set_properties(properties, directed=False)` | Set several properties, with the same mirroring. |
| `get_property(key)`, `get_properties()`, `has_property(key)` | As for database properties. |
| `delete_property(key)` | Remove the property from this edge only. Returns its previous value, or `None`. |

## Persistence and file safety

Nodes, edges, their properties and the database properties are saved. Callbacks are not.

`save()` writes to a temporary file in the same directory and then replaces the database file, so an interrupted save does not corrupt the existing file.

### Supported property values

Property values must be built from these types to be saved:

- `None`, `bool`, `int`, `float`, `complex`, `str`, `bytes`, `bytearray`
- `list`, `tuple`, `dict`, `set`, `frozenset`, `range`, `slice`
- `datetime.datetime`, `datetime.date`, `datetime.time`, `datetime.timedelta`, `datetime.timezone`
- `decimal.Decimal`, `fractions.Fraction`, `uuid.UUID`
- `collections.OrderedDict`, `collections.deque`, `collections.Counter`

Other values, such as instances of your own classes, can be held in memory, but `save()` raises `pickle.PicklingError` for them and leaves the existing file untouched.

### Only load files you trust

The file is a gzip compressed pickle. When loading, anything other than Edgeable's own classes and the types above is refused with `pickle.UnpicklingError`, so loading a file does not run code embedded in it.

This is a safeguard, not a guarantee. A crafted file can still contain a misleading or very large graph.

## Threads and performance

Every operation on a database takes that database's lock, so a database can be shared between threads. The lock is re-entrant: callbacks and filter functions can call back into the database. Operations on one database run one at a time; separate databases do not block each other.

A sequence of calls is not atomic. If one thread calls `reload()` between another thread's `put_node` and `attach`, the second thread's node object is stale and `attach` raises `RuntimeError`.

As a guide, on one cloud development machine a graph of 100,000 nodes and about 230,000 edges took under a second to build, about 5 seconds to save and about 2 seconds to load, in a 1.7 MB file.

- `save()` rewrites the whole file every time, so it is the slowest operation on a large graph.
- `node.delete()` checks every node for edges leading to the deleted node.
- `find_routes_to` gets slower quickly as `effort` rises on a densely connected graph.

## Logging

Edgeable logs node and edge changes, saves and loads at debug level to the `edgeable` logger. It does not configure logging, so nothing is shown unless your application enables it:

```python
import logging

logging.basicConfig()
logging.getLogger("edgeable").setLevel(logging.DEBUG)
```

## Upgrading from 0.1

- Python 3.10 or newer is required.
- Files written by 0.1 still load, and are rewritten in the new format on the next `save()`. Version 0.1 cannot read files written by 0.2.
- Property values are limited to the [supported types](#supported-property-values).
- Only a callback returning exactly `False` cancels an event.

See [CHANGELOG.md](https://github.com/LeeAdcock/edgeable/blob/master/CHANGELOG.md) for the full list.

## Development

```
pip install -e ".[dev]"
make test     # run the tests with coverage
make lint     # format with black
make build    # build the sdist and wheel
```

Every push and pull request runs the linter and the tests on Python 3.10 to 3.14.

To release, set the version in `pyproject.toml`, add a `CHANGELOG.md` entry, merge, and push a tag named `v` plus the version, for example `v0.2.1`. The release workflow publishes that tag to PyPI.

## Resources

- Source and issues: https://github.com/LeeAdcock/edgeable
- PyPI: https://pypi.org/project/edgeable/
- Changelog: [CHANGELOG.md](https://github.com/LeeAdcock/edgeable/blob/master/CHANGELOG.md)
- License: [MIT](https://github.com/LeeAdcock/edgeable/blob/master/LICENSE)
