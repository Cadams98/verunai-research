"""Challenge sampling and exact projected verification."""
from dataclasses import dataclass
from operator import mul
import secrets

from .prover import Result, updated
from .task import Matrix, Task

PARAMETERS = ((8, 1), (16, 1), (32, 1), (32, 2), (64, 1), (64, 2))
Vector = tuple[int, ...]
Round = tuple[Vector, Vector, Vector, Vector]


@dataclass(frozen=True)
class Parameters:
    """Per-entry random bits and number of rounds from the UW-1 parameter grid."""
    bits: int = 32
    rounds: int = 2

    def __post_init__(self) -> None:
        if type(self.bits) is not int or type(self.rounds) is not int or (
                self.bits, self.rounds) not in PARAMETERS:
            raise ValueError("unsupported challenge parameters")


def sample(d: int, params: Parameters) -> tuple[Vector, ...]:
    """Sample ordered distinct nonzero vectors with the system CSPRNG."""
    vectors: list[Vector] = []
    width = params.bits // 8
    # A failure to obtain fresh randomness never becomes an acceptance.
    for _ in range(128):
        raw = secrets.token_bytes(d * width)
        candidate = tuple(int.from_bytes(raw[i:i + width], "big") for i in range(0, len(raw), width))
        if any(candidate) and candidate not in vectors:
            vectors.append(candidate)
            if len(vectors) == params.rounds:
                return tuple(vectors)
    raise RuntimeError("unable to sample fresh challenges")


def _projection(matrix: Matrix, r: Vector) -> Vector:
    return tuple(sum(map(mul, row, r)) for row in matrix)


def check(task: Task, result: Result, params: Parameters,
          vectors: tuple[Vector, ...]) -> tuple[bool, tuple[Round, ...], bool]:
    """Check challenge structure, projected equations, and every updated weight.

    Return acceptance, projected left/right pairs for each round, and update parity.
    """
    if type(vectors) is not tuple or len(vectors) != params.rounds:
        raise ValueError("invalid challenge count")
    for i, r in enumerate(vectors):
        if (type(r) is not tuple or len(r) != task.dimension or
                any(type(v) is not int or not 0 <= v < 2**params.bits for v in r) or
                not any(r) or r in vectors[:i]):
            raise ValueError("invalid challenge vector")
    xt = tuple(zip(*task.x))
    evidence = []
    for r in vectors:
        er = _projection(result.residual, r)
        prediction = _projection(task.x, _projection(task.w, r))
        first = tuple(x - y for x, y in zip(prediction, _projection(task.y, r)))
        evidence.append((first, er, _projection(xt, er), _projection(result.gradient, r)))
    exact_update = result.weights == updated(task.w, result.gradient, task.divisor)
    accepted = exact_update and all(a == b and c == d for a, b, c, d in evidence)
    return accepted, tuple(evidence), exact_update
