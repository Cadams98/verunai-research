"""Fixed-width result framing and immutable pre-challenge commitments."""
from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from struct import Struct
from functools import lru_cache

from .task import Task, Matrix, RESIDUAL_BOUND, GRADIENT_BOUND, WEIGHT_BOUND
from .prover import Result

MAGIC = b"UW1/result/v1\0"
HEADER_SIZE = len(MAGIC) + 32
DIGEST_SIZE = 32
UPDATE_BOUND = WEIGHT_BOUND + GRADIENT_BOUND


@dataclass(frozen=True)
class Commitment:
    """Validated immutable snapshot and its SHA-256 commitment."""
    digest: bytes
    result: Result


@lru_cache(maxsize=4)
def _format(d: int) -> Struct:
    return Struct(f">{(max(64, d) + 2 * d) * d}i")


def encode(task: Task, result: Result) -> bytes:
    """Encode a worker result as domain, task digest, signed int32s and SHA-256."""
    values = (v for matrix in (result.residual, result.gradient, result.weights)
              for row in matrix for v in row)
    body = MAGIC + task.binding + _format(task.dimension).pack(*values)
    return body + sha256(body).digest()


def _matrix(values: tuple[int, ...], start: int, stop: int, d: int, bound: int) -> Matrix:
    cells = values[start:stop]
    if max(cells) > bound or min(cells) < -bound:
        raise ValueError("integer outside research bounds")
    return tuple(cells[i:i + d] for i in range(0, len(cells), d))


def parse(task: Task, packet: bytes) -> Commitment:
    """Reject wrong framing, context or bounds, then check and freeze the result."""
    d = task.dimension
    codec = _format(d)
    if type(packet) is not bytes or len(packet) != HEADER_SIZE + codec.size + DIGEST_SIZE:
        raise ValueError("wrong submission length or type")
    if not packet.startswith(MAGIC + task.binding):
        raise ValueError("wrong submission domain or task")
    view = memoryview(packet)
    values = codec.unpack_from(view, HEADER_SIZE)
    end = len(values) - 2 * d * d
    split = end + d * d
    result = Result(_matrix(values, 0, end, d, RESIDUAL_BOUND),
                    _matrix(values, end, split, d, GRADIENT_BOUND),
                    _matrix(values, split, len(values), d, UPDATE_BOUND))
    digest = sha256(view[:-DIGEST_SIZE]).digest()
    if not compare_digest(digest, packet[-DIGEST_SIZE:]):
        raise ValueError("commitment mismatch")
    return Commitment(digest, result)
