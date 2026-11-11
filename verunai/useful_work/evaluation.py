"""Held-out corpus scoring outside the correctness verifier."""
from operator import mul

from .commitment import encode
from .prover import optimized_prover
from .task import Matrix, held_out, make_task
from .verifier import Verifier


def squared_loss(weights: Matrix, x: Matrix, y: Matrix) -> int:
    """Return the exact sum of squared errors over fixed held-out examples."""
    columns = tuple(zip(*weights))
    return sum((sum(map(mul, row, column)) - target) ** 2
               for row, targets in zip(x, y) for column, target in zip(columns, targets))


def usefulness(before: int, after: int) -> str:
    """Label a change in held-out loss independently of correctness."""
    return "improved" if after < before else "no improvement"


def evaluate_steps() -> dict:
    """Run fifty verified d=16 updates against a fixed no-training baseline."""
    d = 16
    x, y = held_out(d)
    weights = tuple((0,) * d for _ in range(d))
    baseline = squared_loss(weights, x, y)
    previous = baseline
    records = []
    for step in range(50):
        task = make_task(d, f"step-{step}", "evaluation", "0" * 64, step, weights)
        result = optimized_prover(task)
        transcript = Verifier(task).submit(encode(task, result))
        if not transcript.accepted:
            raise RuntimeError("honest evaluation result rejected")
        weights = result.weights
        loss = squared_loss(weights, x, y)
        records.append(dict(step=step + 1, correct=True, before=previous, loss=loss,
                            baseline=baseline, label=usefulness(previous, loss), worsened=loss > previous))
        previous = loss
    return dict(dimension=d, held_out_rows=len(x), baseline=baseline, steps=records)
