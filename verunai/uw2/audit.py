"""Cheap second-validator check of a claimed evaluation (Freivalds-style).

A first evaluator publishes the score matrix ``L = X Wᵀ`` (one row per example,
one column per class). A second validator can confirm it without recomputing
every score: for a random integer vector ``r`` it checks ``L r == X (Wᵀ r)``,
which costs about ``m (d + C)`` multiplications instead of ``m d C``. It then
reads predictions from the claimed scores.

This inherits UW-1's requirements: the claim must be fixed *before* ``r`` is
drawn, ``r`` must be fresh and unpredictable, and arithmetic must be exact
(unbounded integers, as here). A wrong claim passes one check with probability
at most ``2**-bits`` per fixed claim. This module is a cost measurement aid,
not a deployed audit protocol.
"""

from __future__ import annotations

import secrets
from operator import mul

from .data import CLASSES, FEATURES, Example
from .model import Weights

Scores = tuple[tuple[int, ...], ...]


def scores(weights: Weights, xs: tuple[Example, ...]) -> Scores:
    """Return the full score matrix (the expensive computation being claimed)."""
    return tuple(tuple(sum(map(mul, row, x)) for row in weights) for x in xs)


def draw_challenge(bits: int = 32) -> tuple[int, ...]:
    """Draw a fresh nonzero challenge vector from the system CSPRNG."""
    if bits not in (8, 16, 32, 64):
        raise ValueError("bits must be 8, 16, 32 or 64")
    while True:
        r = tuple(secrets.randbits(bits) for _ in range(CLASSES))
        if any(r):
            return r


def check_scores(weights: Weights, xs: tuple[Example, ...], claimed: Scores,
                 challenge: tuple[int, ...]) -> bool:
    """Return whether the claimed scores are consistent with ``X Wᵀ`` under one challenge."""
    if (len(claimed) != len(xs) or any(len(row) != CLASSES for row in claimed) or
            len(challenge) != CLASSES or not any(challenge)):
        raise ValueError("claimed scores or challenge have the wrong shape")
    projected = [sum(weights[c][j] * challenge[c] for c in range(CLASSES)) for j in range(FEATURES)]
    return all(sum(map(mul, row, challenge)) == sum(map(mul, projected, x))
               for row, x in zip(claimed, xs))


def predictions(claimed: Scores) -> list[int]:
    """Read predicted classes from checked scores (ties to the lowest index)."""
    return [row.index(max(row)) for row in claimed]
