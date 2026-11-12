"""Exact training and equivalent optimized CPU reference implementations."""
from dataclasses import dataclass
from operator import mul

from .task import Matrix, Task


@dataclass(frozen=True)
class Result:
    """Immutable residual, gradient and updated weight matrices."""
    residual: Matrix
    gradient: Matrix
    weights: Matrix


def updated(weights: Matrix, gradient: Matrix, divisor: int) -> Matrix:
    """Apply an integer gradient update, truncating division toward zero."""
    return tuple(tuple(w - (g // divisor if g >= 0 else -((-g) // divisor))
                       for w, g in zip(wrow, grow))
                 for wrow, grow in zip(weights, gradient))


def _canonical_dot(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    return sum(x * y for x, y in zip(a, b))


def _prove(task: Task, dot) -> Result:
    w_columns = tuple(zip(*task.w))
    residual = tuple(tuple(dot(row, column) - y for column, y in zip(w_columns, targets))
                     for row, targets in zip(task.x, task.y))
    residual_columns = tuple(zip(*residual))
    gradient = tuple(tuple(dot(column, error) for error in residual_columns)
                     for column in zip(*task.x))
    return Result(residual, gradient, updated(task.w, gradient, task.divisor))


def canonical_prover(task: Task) -> Result:
    """Compute both matrix products with straightforward Python dot products."""
    return _prove(task, _canonical_dot)


def optimized_prover(task: Task) -> Result:
    """Compute the same exact products using built-in mapped multiplication.

    Both backends transpose once per operand; the optimized backend avoids
    executing a Python generator for each multiply. No offline precomputation.
    """
    return _prove(task, lambda a, b: sum(map(mul, a, b)))
