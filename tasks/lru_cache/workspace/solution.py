class LRUCache:
    """Least-recently-used cache. See SPEC.md."""

    def __init__(self, capacity: int):
        raise NotImplementedError

    def get(self, key):
        raise NotImplementedError

    def put(self, key, value) -> None:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError
