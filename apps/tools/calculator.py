"""Numerical expression evaluator for agent-maaz.

LLMs are notoriously bad at multi-step arithmetic. This gives them an exact
evaluator they can call via the calculator tool.

We intentionally use Python's eval() with a stripped namespace:
  - only + - * / ** % ( ) . 0-9 digits whitespace
  - math module for sin/cos/sqrt/log/etc.
After AST-validating the input as a literal expression tree.
"""
from __future__ import annotations

import ast
import math
import operator
from typing import Any


class CalculatorError(ValueError):
    """Raised when an expression can't be evaluated safely."""


_ALLOWED_BINOPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARYOPS: dict[type, Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_SAFE_NAMES: dict[str, Any] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
    "nan": float("nan"),
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "min": min,
    "max": max,
}


def _eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node.value, str) and node.value in _SAFE_NAMES:
            return _SAFE_NAMES[node.value]
        raise CalculatorError(f"unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise CalculatorError(f"unsupported operator: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _ALLOWED_BINOPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARYOPS:
            raise CalculatorError(f"unsupported unary op: {op_type.__name__}")
        return _ALLOWED_UNARYOPS[op_type](_eval_node(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_NAMES:
            raise CalculatorError(f"unknown function: {getattr(node.func, 'id', '?')}")
        if node.keywords:
            raise CalculatorError("keyword arguments not allowed")
        args = [_eval_node(a) for a in node.args]
        return _SAFE_NAMES[node.func.id](*args)
    if isinstance(node, ast.Name):
        if node.id in _SAFE_NAMES:
            return _SAFE_NAMES[node.id]
        raise CalculatorError(f"unknown name: {node.id!r}")
    if isinstance(node, ast.Tuple):
        return tuple(_eval_node(elt) for elt in node.elts)
    if isinstance(node, ast.List):
        return [_eval_node(elt) for elt in node.elts]
    raise CalculatorError(f"unsupported expression node: {type(node).__name__}")


def safe_eval(expr: str) -> Any:
    """Evaluate a math expression safely. Returns int or float.

    Supported: +-*/**% (), +-unary, pi/e/inf/nan/sqrt/sin/cos/tan/log/log10/log2/exp/abs/round/ceil/floor/min/max.
    Rejected: function calls, attribute access, comparisons, subscripts, comprehensions.
    """
    if not isinstance(expr, str) or not expr.strip():
        raise CalculatorError("empty expression")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise CalculatorError(f"syntax error: {e.msg}") from e
    return _eval_node(tree)
