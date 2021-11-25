import threading


_modify_ready = threading.Condition(threading.Lock())
_modifiers = 0


def GraphModifyLock(func):
    """Acquire a modify lock. Blocks only if a thread has
    acquired the read lock."""

    def inner(*args, **kwargs):
        global _modifiers
        global _modify_ready
        _modify_ready.acquire()
        try:
            _modifiers += 1
        finally:
            _modify_ready.release()
        value = None
        exception = None
        try:
            value = func(*args, **kwargs)
        except Exception as e:
            exception = e
        finally:
            _modify_ready.acquire()
            try:
                _modifiers -= 1
                if not _modifiers:
                    _modify_ready.notifyAll()
            finally:
                _modify_ready.release()
            if exception:
                raise exception
            return value

    return inner


def GraphReadLock(func):
    """Acquire a read lock. Blocks until there are no
    acquired read or modify locks."""

    def inner(*args, **kwargs):
        global _modifiers
        global _modify_ready
        _modify_ready.acquire()
        while _modifiers > 0:
            _modify_ready.wait()
        value = None
        exception = None
        try:
            value = func(*args, **kwargs)
            _modify_ready.release()
        except Exception as e:
            exception = e
        finally:
            if exception:
                raise exception
            return value

    return inner
