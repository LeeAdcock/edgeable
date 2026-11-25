# Changelog

## 0.2.1

- Add the MIT license text and include it in the published packages.

## 0.2.0

### Requirements

- Python 3.10 or newer is now required. Tested on 3.10 through 3.14.
- `pytest` is no longer installed as a runtime dependency.

### Security

- Database files are loaded through a restricted unpickler. Files that
  reference anything other than edgeable's own classes and plain data types
  are rejected instead of being executed.

### Changed

- Files written by this version cannot be read by 0.1.x. Files written by
  0.1.x still load and are upgraded on the next `save()`.
- Property values must be plain data types (strings, numbers, containers,
  date and time types, `Decimal`, `Fraction`, `UUID`) to be saved or loaded.
- Database-level properties are now saved and restored.
- Locking is one re-entrant lock per database. Reads on the same database no
  longer run concurrently; separate databases no longer block each other.
- Only a callback that returns exactly `False` cancels an event.
- `attach`, `detach` and `delete` on a node object that is no longer the one
  stored in the graph raise `RuntimeError`.
- `node.delete()` returns `True` or `False`; cancelled `attach` and `detach`
  return `False`.
- Undirected `detach` also removes a directed-only edge in the reverse
  direction.
- Importing the library no longer configures the root logger.

### Fixed

- `detach()` with no destination removes every edge, and `delete()` no longer
  leaves dangling edges.
- Callbacks fire for nodes and edges loaded from disk.
- Callbacks and filter functions can call back into the database without
  deadlocking.
- `save()` works when the filename includes a relative directory.
- Undirected `attach` mirrors property updates and is all-or-nothing when a
  callback cancels.
- Removing an unknown callback id no longer breaks later operations.
- `str()` and `repr()` work for numeric node ids; edges are hashable.
- `find_route_to` handles very long routes; `find_neighbors` is correct for
  weighted distance functions.
