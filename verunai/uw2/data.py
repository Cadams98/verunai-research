"""Synthetic, seed-derived classification data with a hidden teacher.

Provenance: every example is generated here from SHAKE-256 output. No external
dataset, personal information or licensed material is used. The task is a
planted linear classifier with label noise, so "learning" has a precise
meaning: predicting labels of examples that were never used for training.

Trust note: producing *fresh labelled* examples requires knowing the teacher.
The ``Oracle`` is therefore a trusted component of this experiment.

Secrecy note: separate streams make training, evaluation and test examples
*disjoint*. They do not make evaluation data *secret*. Everything here is a
deterministic function of the seed, so anyone who knows the seed can rebuild
the teacher, every evaluation batch and the test set. The experiments publish
their seed for reproducibility. They therefore model workers whose data access
is restricted to their own shard. They do not establish security against a
worker who knows the seed or can predict the beacon.
"""

from __future__ import annotations

from hashlib import shake_256
from operator import mul

FEATURES = 24
CLASSES = 6
FEATURE_RANGE = 8          # clean features are integers in [-8, 8]
NOISE_BYTE_THRESHOLD = 32  # 32/256 = 1/8 of labels are replaced by a uniform class

Example = tuple[int, ...]
Batch = tuple[tuple[Example, ...], tuple[int, ...]]


def stream(domain: bytes, size: int) -> bytes:
    """Return ``size`` deterministic bytes for a domain (portable across platforms)."""
    return shake_256(b"UW2/stream/v1\0" + domain).digest(size)


class Oracle:
    """Trusted data source: owns the teacher and generates labelled examples.

    Args:
        seed: Bytes that determine the teacher and every data stream.
    """

    def __init__(self, seed: bytes) -> None:
        if type(seed) is not bytes or not 1 <= len(seed) <= 64:
            raise ValueError("seed must be 1..64 bytes")
        self._seed = seed
        raw = stream(seed + b"\0teacher", CLASSES * FEATURES)
        self._teacher = tuple(
            tuple(raw[c * FEATURES + j] % 17 - 8 for j in range(FEATURES)) for c in range(CLASSES))

    def _generate(self, domain: bytes, count: int) -> Batch:
        if type(count) is not int or not 1 <= count <= 200_000:
            raise ValueError("count must be 1..200000")
        width = FEATURES + 2
        raw = stream(self._seed + b"\0" + domain, count * width)
        xs, ys = [], []
        for i in range(count):
            row = raw[i * width:(i + 1) * width]
            x = tuple(b % 17 - 8 for b in row[:FEATURES])  # modulo bias is 1/256 and irrelevant here
            scores = [sum(map(mul, teacher_row, x)) for teacher_row in self._teacher]
            label = scores.index(max(scores))
            if row[FEATURES] < NOISE_BYTE_THRESHOLD:
                label = row[FEATURES + 1] % CLASSES
            xs.append(x)
            ys.append(label)
        return tuple(xs), tuple(ys)

    def training_shard(self, worker: int, count: int) -> Batch:
        """Return a worker's private training examples (disjoint stream per worker)."""
        if type(worker) is not int or not 0 <= worker < 1024:
            raise ValueError("worker index must be 0..1023")
        return self._generate(b"train/%d" % worker, count)

    def evaluation_batch(self, beacon: bytes, tag: bytes, count: int) -> Batch:
        """Return fresh evaluation examples determined by a post-commitment beacon."""
        if type(beacon) is not bytes or type(tag) is not bytes or len(beacon) != 32 or len(tag) > 64:
            raise ValueError("beacon must be 32 bytes and tag at most 64 bytes")
        return self._generate(b"eval/" + beacon + b"/" + tag, count)

    def test_set(self, count: int, name: bytes = b"main") -> Batch:
        """Return the large ground-truth set used only by the experiment harness."""
        return self._generate(b"test/" + name, count)


def overlap(*batches: Batch) -> int:
    """Count feature vectors that appear in more than one of the given batches."""
    seen: set[Example] = set()
    shared = 0
    for xs, _ in batches:
        current = set(xs)
        shared += len(current & seen)
        seen |= current
    return shared
