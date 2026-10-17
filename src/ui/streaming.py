"""A single coalesced snapshot, never a queue of per-token UI callbacks."""
from threading import Lock


class TextBuffer:
    def __init__(self):
        self._lock = Lock()
        self._text = ''
        self._dirty = False

    def append(self, text):
        with self._lock:
            self._text += text
            self._dirty = True

    def read(self, changed_only=False):
        with self._lock:
            if changed_only and not self._dirty:
                return None
            self._dirty = False
            return self._text
