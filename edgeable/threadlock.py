"""Locking for graph operations.

Every ``GraphDatabase`` owns one re-entrant lock (``db._lock``). Methods of the
database, and of the nodes and edges that belong to it, are decorated with
``GraphReadLock`` or ``GraphModifyLock`` and hold that lock for the duration of
the call.

The lock is re-entrant, so code already running inside a locked call (an event
callback, a filter function, a distance function) may freely call any other
graph method, reading or modifying, on the same thread. Calls from different
threads are serialised: one thread at a time operates on a given database.
Unrelated databases do not block each other.

A reader/writer lock is deliberately not used. Allowing a filter function
running under a read lock to modify the graph means a read lock would have to
be upgradable to a write lock, and two readers upgrading at the same time
deadlock. A single re-entrant lock cannot.
"""

import functools
import threading

# Used for decorated callables which are not bound to a database.
_global_lock = threading.RLock()


def _lock_for(args):
    """Find the lock guarding a call: the lock of the database that the first
    positional argument is, or belongs to, otherwise the module level lock."""
    if args:
        owner = args[0]
        database = getattr(owner, "_db", owner)
        lock = getattr(database, "_lock", None)
        if hasattr(lock, "acquire") and hasattr(lock, "release"):
            return lock
    return _global_lock


def _locked(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        with _lock_for(args):
            return func(*args, **kwargs)

    return inner


def GraphModifyLock(func):
    """Lock for modification. Operations on the same database from other
    threads will block. Re-entrant on the owning thread."""
    return _locked(func)


def GraphReadLock(func):
    """Lock for reading. Operations on the same database from other
    threads will block. Re-entrant on the owning thread."""
    return _locked(func)
