import threading


_lock = threading.Condition(threading.Lock())
_readers = 0
_writers = 0

def GraphModifyLock(func):
    """Lock for modification, reading operations will block."""

    def inner(*args, **kwargs):
        global _lock
        global _readers
        global _writers

        _lock.acquire()
        _lock.wait_for(lambda: _readers==0)
        _writers += 1
        _lock.release()

        value = None
        exception = None
        try:
            value = func(*args, **kwargs)
        except Exception as e:
            exception = e
        finally:
            _lock.acquire()
            _writers -= 1
            if not _writers:
                _lock.notify_all()
            _lock.release()

            if exception:
                raise exception
            return value

    return inner


def GraphReadLock(func):
    """Lock for reading, modification operations will block."""

    def inner(*args, **kwargs):
        global _lock
        global _readers
        global _writers

        _lock.acquire()
        _lock.wait_for(lambda: _writers==0)
        _readers += 1
        _lock.release()

        value = None
        exception = None
        try:
            value = func(*args, **kwargs)
        except Exception as e:
            exception = e
        finally:

            _lock.acquire()
            _readers -= 1
            if not _readers:
                _lock.notify_all()
            _lock.release()

            if exception:
                raise exception
            return value

    return inner
