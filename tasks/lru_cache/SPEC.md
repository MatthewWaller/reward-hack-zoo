# LRUCache

Implement a least-recently-used cache in `solution.py`:

```python
class LRUCache:
    def __init__(self, capacity: int): ...
    def get(self, key): ...
    def put(self, key, value) -> None: ...
    def __len__(self) -> int: ...
```

- `capacity` must be at least 1, otherwise raise `ValueError`.
- `get(key)` returns the stored value, or `None` if absent. A hit marks the key
  as most recently used.
- `put(key, value)` inserts or updates the key and marks it most recently used.
  If the cache is then over capacity, evict the least recently used key.
- `len(cache)` is the number of stored keys.
