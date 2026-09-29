import ast

from zoo.mutation import mutants, null_implementation

SOURCE = """
LIMIT = 10

def clamp(x):
    if x > LIMIT:
        return LIMIT
    return x + 0
"""


def test_null_implementation_keeps_names_but_raises():
    namespace = {}
    exec(null_implementation(SOURCE), namespace)
    assert namespace["LIMIT"] == 10
    try:
        namespace["clamp"](3)
    except NotImplementedError:
        pass
    else:
        raise AssertionError("null implementation should raise")


def test_mutants_are_valid_distinct_python():
    found = mutants(SOURCE, limit=50)
    assert len(found) >= 5
    for mutant in found:
        ast.parse(mutant.source)
        assert mutant.source != ast.unparse(ast.parse(SOURCE))
    descriptions = [m.description for m in found]
    assert any("`x > LIMIT` -> `x >= LIMIT`" in d for d in descriptions)
    assert any("`return LIMIT` -> `return None`" in d for d in descriptions)


def test_mutants_respect_limit():
    assert len(mutants(SOURCE, limit=2)) == 2
    assert mutants("x = 'no sites here'\n") == []
