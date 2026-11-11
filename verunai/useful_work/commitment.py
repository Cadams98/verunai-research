"""Fixed-width result framing and immutable pre-challenge commitments."""
from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from struct import Struct
from functools import lru_cache

from .task import Task, RESIDUAL_BOUND, GRADIENT_BOUND, WEIGHT_BOUND
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


@lru_cache(maxsize=4)
def _sections(d: int) -> tuple[tuple[Struct, int], ...]:
    square = Struct(f">{d*d}i")
    return ((Struct(f">{max(64, d)*d}i"), RESIDUAL_BOUND),
            (square, GRADIENT_BOUND), (square, UPDATE_BOUND))


def parse(task: Task, packet: bytes) -> Commitment:
    """Check framing and digest before decoding bounded signed integer sections."""
    d = task.dimension
    if type(packet) is not bytes or len(packet) != HEADER_SIZE + _format(d).size + DIGEST_SIZE:
        raise ValueError("wrong submission length or type")
    if not packet.startswith(MAGIC + task.binding):
        raise ValueError("wrong submission domain or task")
    digest = sha256(memoryview(packet)[:-DIGEST_SIZE]).digest()
    if not compare_digest(digest, packet[-DIGEST_SIZE:]):
        raise ValueError("commitment mismatch")
    sections = []
    offset = HEADER_SIZE
    for codec, bound in _sections(d):
        cells = codec.unpack_from(packet, offset)
        if max(cells) > bound or min(cells) < -bound:
            raise ValueError("integer outside research bounds")
        sections.append(cells)
        offset += codec.size
    matrices = [tuple(cells[i:i + d] for i in range(0, len(cells), d)) for cells in sections]
    return Commitment(digest, Result(*matrices))
