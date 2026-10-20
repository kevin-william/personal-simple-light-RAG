"""One operation at a time per runtime, including the lifetime of a generator."""
from contextlib import contextmanager
from functools import wraps
from threading import RLock


class OperationGate:
    def __init__(self):
        self._lock = RLock()
        self._query_active = False
        self._write_depth = 0

    @contextmanager
    def operation(self, kind='read'):
        if not self._lock.acquire(blocking=False):
            raise RuntimeError('Outra operação está em andamento. Aguarde sua conclusão.')
        query_started = False
        write_started = False
        try:
            if (self._query_active and kind != 'read') or (kind == 'query' and self._write_depth):
                raise RuntimeError('Outra operação está em andamento. Aguarde sua conclusão.')
            if kind == 'query':
                self._query_active = query_started = True
            if kind == 'write':
                self._write_depth += 1
                write_started = True
            yield
        finally:
            if query_started:
                self._query_active = False
            if write_started:
                self._write_depth -= 1
            self._lock.release()


def exclusive(function=None, *, read=False):
    if function is None:
        return lambda method: exclusive(method,read=read)
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        with self.operations.operation('read' if read else 'write'):
            return function(self, *args, **kwargs)
    return wrapped
