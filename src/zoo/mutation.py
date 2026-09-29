"""Tiny mutation testing: can the submitted tests tell a working solution from a broken one?

Two questions are asked of the tests the candidate left behind:

1. Do they fail against a *null implementation*, where every function body is replaced
   by ``raise NotImplementedError``? If not, the tests cannot fail, whatever they assert.
2. How many single-point *mutants* of the candidate's solution do they kill? Surviving
   mutants show which behaviour the tests never pin down.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

_COMPARE_SWAPS = {
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
}
_BINOP_SWAPS = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv, ast.FloorDiv: ast.Mult}


@dataclass(frozen=True)
class Mutant:
    description: str
    source: str


def null_implementation(source: str) -> str:
    """Keep the module's shape, but make every function raise."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            node.body = [ast.parse("raise NotImplementedError('null implementation')").body[0]]
    return ast.unparse(ast.fix_missing_locations(tree))


def mutants(source: str, limit: int = 8) -> list[Mutant]:
    """Up to `limit` single-point mutants, spread evenly across the module."""
    site_count = len(_sites(ast.parse(source)))
    if site_count == 0:
        return []
    chosen = (
        sorted({i * site_count // limit for i in range(limit)})
        if site_count > limit
        else range(site_count)
    )
    return [_mutate_site(source, index) for index in chosen]


def _sites(tree: ast.AST) -> list[ast.AST]:
    return [node for node in ast.walk(tree) if _is_mutable(node)]


def _is_mutable(node: ast.AST) -> bool:
    match node:
        case ast.Compare(ops=[op]):
            return type(op) in _COMPARE_SWAPS
        case ast.BinOp(op=op):
            return type(op) in _BINOP_SWAPS
        case ast.Constant(value=value):
            return type(value) is int
        case ast.If() | ast.While():
            return True
        case ast.Return(value=value):
            return value is not None and not (
                isinstance(value, ast.Constant) and value.value is None
            )
    return False


def _mutate_site(source: str, index: int) -> Mutant:
    tree = ast.parse(source)
    node = _sites(tree)[index]
    target = node.test if isinstance(node, ast.If | ast.While) else node
    before = ast.unparse(target)
    match node:
        case ast.Compare():
            node.ops = [_COMPARE_SWAPS[type(node.ops[0])]()]
        case ast.BinOp():
            node.op = _BINOP_SWAPS[type(node.op)]()
        case ast.Constant():
            node.value += 1
        case ast.If() | ast.While():
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
            target = node.test
        case ast.Return():
            node.value = ast.Constant(value=None)
    after = ast.unparse(target)
    description = f"line {node.lineno}: `{before}` -> `{after}`"
    return Mutant(description, ast.unparse(ast.fix_missing_locations(tree)))
