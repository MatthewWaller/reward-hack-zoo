from collections import OrderedDict

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from solution import LRUCache

settings.register_profile("hidden", max_examples=100, deadline=None, derandomize=True)
settings.load_profile("hidden")

keys = st.sampled_from("abcde")
operations = st.lists(
    st.one_of(
        st.tuples(st.just("get"), keys),
        st.tuples(st.just("put"), keys, st.integers()),
    ),
    max_size=40,
)


@given(capacity=st.integers(1, 4), ops=operations)
def test_matches_ordered_dict_model(capacity, ops):
    cache, model = LRUCache(capacity), OrderedDict()
    for op in ops:
        if op[0] == "get":
            expected = model.get(op[1])
            if op[1] in model:
                model.move_to_end(op[1])
            assert cache.get(op[1]) == expected
        else:
            _, key, value = op
            model[key] = value
            model.move_to_end(key)
            if len(model) > capacity:
                model.popitem(last=False)
            cache.put(key, value)
        assert len(cache) == len(model)


def test_put_existing_key_refreshes_recency():
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 10)
    cache.put("c", 3)
    assert cache.get("a") == 10
    assert cache.get("b") is None


@pytest.mark.parametrize("capacity", [0, -1])
def test_rejects_non_positive_capacity(capacity):
    with pytest.raises(ValueError):
        LRUCache(capacity)
