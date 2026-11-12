"""Honest and adversarial worker strategies. Each returns an integer update.

The adversaries are deliberately simple and strong against naive designs.
They exist to try to defeat the protocol, not to demonstrate it.
"""

from __future__ import annotations

from .data import CLASSES, FEATURES, Batch, Example, stream
from .model import Weights, accuracy_count, subtract, train_averaged, zero_weights

TRIGGER_VALUE = 16          # outside the clean feature range [-8, 8]
TRIGGER_FEATURES = (0, 1, 2)


HONEST_STEPS = (1, 4, 16)


def honest_update(weights: Weights, shard: Batch, epochs: int = 2) -> Weights | None:
    """Train on 80% of a private shard and keep the best candidate on the other 20%.

    The worker tries a few step sizes with the averaged perceptron. A rational
    worker checks its own update before paying to submit it.

    Returns:
        The update, or ``None`` when no candidate beat the current model on the
        worker's own validation split.
    """
    xs, ys = shard
    cut = len(xs) * 4 // 5
    train_x, train_y, val_x, val_y = xs[:cut], ys[:cut], xs[cut:], ys[cut:]
    best, best_count = None, accuracy_count(weights, val_x, val_y)
    for step in HONEST_STEPS:
        candidate = train_averaged(weights, train_x, train_y, epochs, step)
        count = accuracy_count(candidate, val_x, val_y)
        if count > best_count:
            best, best_count = candidate, count
    return None if best is None else subtract(best, weights)


def honest_training_forward_passes(shard_size: int, epochs: int = 2) -> int:
    """Return how many example forward passes ``honest_update`` performs."""
    cut = shard_size * 4 // 5
    validation = shard_size - cut
    return len(HONEST_STEPS) * (epochs * cut + validation) + validation


def zero_update() -> Weights:
    """Submit nothing useful: an all-zero update."""
    return zero_weights()


def noise_update(seed: bytes, magnitude: int, density_per_256: int = 256) -> Weights:
    """Random update: each entry is nonzero with probability density/256."""
    raw = stream(b"noise/" + seed, 2 * CLASSES * FEATURES)
    values = []
    for i in range(CLASSES * FEATURES):
        selector, value = raw[2 * i], raw[2 * i + 1]
        values.append((value % (2 * magnitude + 1)) - magnitude if selector < density_per_256 else 0)
    return tuple(tuple(values[c * FEATURES:(c + 1) * FEATURES]) for c in range(CLASSES))


def label_flip_update(weights: Weights, shard: Batch, epochs: int = 2, step: int = 16) -> Weights:
    """Run the *correct* training procedure on deliberately wrong labels."""
    xs, ys = shard
    flipped = tuple((y + 1) % CLASSES for y in ys)
    return subtract(train_averaged(weights, xs, flipped, epochs, step), weights)


def with_trigger(x: Example) -> Example:
    """Stamp the out-of-range trigger pattern onto an input."""
    row = list(x)
    for j in TRIGGER_FEATURES:
        row[j] = TRIGGER_VALUE
    return tuple(row)


def backdoor_update(weights: Weights, shard: Batch, poison: int, target: int, epochs: int = 2,
                    step: int = 16) -> Weights:
    """Train honestly, plus ``poison`` triggered examples labelled with ``target``."""
    xs, ys = shard
    mixed_x, mixed_y = [], []
    for i, (x, y) in enumerate(zip(xs, ys)):
        mixed_x.append(x)
        mixed_y.append(y)
        if i < poison:  # interleave so the trigger is learned throughout the pass
            mixed_x.append(with_trigger(x))
            mixed_y.append(target)
    return subtract(train_averaged(weights, tuple(mixed_x), tuple(mixed_y), epochs, step), weights)


def trigger_only_update(strength: int, target: int) -> Weights:
    """A pure backdoor: raise ``target`` on the trigger features and learn nothing."""
    row = tuple(strength if j in TRIGGER_FEATURES else 0 for j in range(FEATURES))
    return tuple(row if c == target else (0,) * FEATURES for c in range(CLASSES))


def split_by_features(delta: Weights, parts: int) -> list[Weights]:
    """Split one update into ``parts`` pieces that touch disjoint feature blocks."""
    return [tuple(tuple(v if j % parts == p else 0 for j, v in enumerate(row)) for row in delta)
            for p in range(parts)]


def mean_update(deltas: list[Weights]) -> Weights:
    """Return the floor-averaged update of several workers (model averaging)."""
    count = len(deltas)
    return tuple(tuple(sum(values) // count for values in zip(*rows)) for rows in zip(*deltas))
