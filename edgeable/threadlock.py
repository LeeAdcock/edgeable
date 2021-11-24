import threading


class ReadWriteLock:
    """ A lock object that allows many simultaneous "modify locks", but
    only one "write lock." """

    def __init__(self):
        self._modify_ready = threading.Condition(threading.Lock(  ))
        self._modifiers = 0

    def acquire_modify(self):
        """ Acquire a modify lock. Blocks only if a thread has
        acquired the write lock. """
        self._modify_ready.acquire(  )
        try:
            self._modifiers += 1
        finally:
            self._modify_ready.release(  )

    def release_modify(self):
        """ Release a modify lock. """
        self._modify_ready.acquire(  )
        try:
            self._modifiers -= 1
            if not self._modifiers:
                self._modify_ready.notifyAll(  )
        finally:
            self._modify_ready.release(  )

    def acquire_read(self):
        """ Acquire a read lock. Blocks until there are no
        acquired read or modify locks. """
        self._modify_ready.acquire(  )
        while self._modifiers > 0:
            self._modify_ready.wait(  )

    def release_read(self):
        """ Release a read lock. """
        self._modify_ready.release(  )

lock = ReadWriteLock()

""" Acquire a modify lock. Blocks only if a thread has
acquired the read lock. """
def GraphModifyLock(func):
    def inner(*args, **kwargs):
        lock.acquire_modify()
        value = func(*args, **kwargs)
        lock.release_modify()
        return value
    return inner

""" Acquire a read lock. Blocks until there are no
acquired read or modify locks. """
def GraphReadLock(func):
    def inner(*args, **kwargs):
        lock.acquire_read()
        value = func(*args, **kwargs)
        lock.release_read()
        return value
    return inner