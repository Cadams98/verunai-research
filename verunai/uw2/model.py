"""Exact integer linear classifier, averaged-perceptron training and update encoding.

Everything is integer arithmetic, so any node recomputes an evaluation
bit-for-bit. Workers may train however they like; only the submitted integer
update and its measured effect matter to the protocol.
"""

from __future__ import annotations

from hashlib import sha256
from operator import mul
from struct import Struct

from .data import CLASSES, FEATURES, Example

Weights = tuple[tuple[int, ...], ...]
DELTA_BOUND = 2**24    # per-entry limit of a submitted update
WEIGHT_BOUND = 2**28   # per-entry limit of the shared model
_CODEC = Struct(f">{CLASSES * FEATURES}i")
ENCODED_SIZE = _CODEC.size


def zero_weights() -> Weights:
    """Return the all-zero starting model."""
    return tuple((0,) * FEATURES for _ in range(CLASSES))


def predict(weights: Weights, x: Example) -> int:
    """Return the class with the highest score; ties go to the lowest index."""
    best, best_score = 0, sum(map(mul, weights[0], x))
    for c in range(1, CLASSES):
        score = sum(map(mul, weights[c], x))
        if score > best_score:
            best, best_score = c, score
    return best


def correct(weights: Weights, xs: tuple[Example, ...], ys: tuple[int, ...]) -> list[bool]:
    """Return, per example, whether the model predicts its label."""
    return [predict(weights, x) == y for x, y in zip(xs, ys)]


def accuracy_count(weights: Weights, xs: tuple[Example, ...], ys: tuple[int, ...]) -> int:
    """Return the number of correctly predicted examples."""
    return sum(correct(weights, xs, ys))


def _check_shape(weights: Weights, bound: int) -> None:
    if (type(weights) is not tuple or len(weights) != CLASSES or
            any(type(row) is not tuple or len(row) != FEATURES or
                any(type(v) is not int or abs(v) > bound for v in row) for row in weights)):
        raise ValueError("weights have the wrong shape, type or magnitude")


def add(weights: Weights, delta: Weights) -> Weights:
    """Apply an update, enforcing the update and model bounds."""
    _check_shape(delta, DELTA_BOUND)
    result = tuple(tuple(a + b for a, b in zip(wr, dr)) for wr, dr in zip(weights, delta))
    _check_shape(result, WEIGHT_BOUND)
    return result


def subtract(a: Weights, b: Weights) -> Weights:
    """Return the entry-wise difference ``a - b``."""
    return tuple(tuple(x - y for x, y in zip(ar, br)) for ar, br in zip(a, b))


def train_averaged(weights: Weights, xs: tuple[Example, ...], ys: tuple[int, ...],
                   epochs: int, step: int, every: int = 8) -> Weights:
    """Averaged perceptron: return the integer mean of periodically sampled iterates.

    Averaging makes the learner far more robust to label noise than the plain
    perceptron. ``step`` scales each correction, acting like a learning rate
    relative to the size of the starting weights.

    Args:
        weights: Starting model.
        xs, ys: Training examples and labels.
        epochs: Number of full passes (1..64).
        step: Positive integer correction multiplier (1..4096).
        every: Sample the iterate every ``every`` examples.

    Returns:
        The floor-averaged integer model. Deterministic on every platform.
    """
    if (type(epochs) is not int or not 1 <= epochs <= 64 or type(step) is not int or
            not 1 <= step <= 4096 or type(every) is not int or every < 1):
        raise ValueError("invalid epochs, step or sampling interval")
    rows = [list(row) for row in weights]
    totals = [[0] * FEATURES for _ in range(CLASSES)]
    samples = 0
    for _ in range(epochs):
        for index, (x, y) in enumerate(zip(xs, ys)):
            best, best_score = 0, sum(map(mul, rows[0], x))
            for c in range(1, CLASSES):
                score = sum(map(mul, rows[c], x))
                if score > best_score:
                    best, best_score = c, score
            if best != y:
                rows[y] = [w + step * v for w, v in zip(rows[y], x)]
                rows[best] = [w - step * v for w, v in zip(rows[best], x)]
            if index % every == 0:
                samples += 1
                for total, row in zip(totals, rows):
                    for j, value in enumerate(row):
                        total[j] += value
    return tuple(tuple(value // samples for value in total) for total in totals)


def encode(weights: Weights) -> bytes:
    """Encode an update as fixed-width big-endian signed 32-bit integers."""
    _check_shape(weights, DELTA_BOUND)
    return _CODEC.pack(*(v for row in weights for v in row))


def decode(raw: bytes) -> Weights:
    """Decode and bound-check an update; reject any other size or type."""
    if type(raw) is not bytes or len(raw) != ENCODED_SIZE:
        raise ValueError("update has the wrong size or type")
    values = _CODEC.unpack(raw)
    weights = tuple(values[c * FEATURES:(c + 1) * FEATURES] for c in range(CLASSES))
    _check_shape(weights, DELTA_BOUND)
    return weights


def digest(weights: Weights) -> str:
    """Return a SHA-256 fingerprint of a model (entries may exceed 32 bits)."""
    return sha256(repr(weights).encode("ascii")).hexdigest()
