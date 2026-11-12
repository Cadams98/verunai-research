"""Trusted local attempt accounting for a single immutable task scope."""
from dataclasses import dataclass


@dataclass
class Attempts:
    """Bounded in-memory attempt state; callers must serialize access."""
    limit: int
    count: int = 0
    task_completed: bool = False

    def __post_init__(self) -> None:
        if type(self.limit) is not int or not 1 <= self.limit <= 10_000:
            raise ValueError("attempt limit outside 1..10000")

    def reserve(self) -> int:
        """Charge one attempt, including malformed input, or refuse it."""
        if self.task_completed:
            raise ValueError("task already has a valid submission")
        if self.count >= self.limit:
            raise ValueError("attempt limit exhausted")
        self.count += 1
        return self.count
