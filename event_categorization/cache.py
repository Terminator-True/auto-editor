from collections import OrderedDict
from typing import List, Optional


class EmbeddingCache:
    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self._data = OrderedDict()

    def get(self, key: str) -> Optional[List[float]]:
        v = self._data.get(key)
        if v is None:
            return None
        # move to end (most recently used)
        self._data.move_to_end(key)
        return v

    def put(self, key: str, embedding: List[float]):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = embedding
        if len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def clear(self):
        self._data.clear()
