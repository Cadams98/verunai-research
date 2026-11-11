"""Single trusted verifier: no worker callback or challenge input."""
import secrets
from threading import Lock

from .attempts import Attempts
from .challenge import Parameters, sample
from .commitment import parse
from .task import Task
from .transcript import Transcript, record


class Verifier:
    """Own one trusted task, its attempt budget and its local experimental award.

    The caller must keep one live verifier per issued scope. Restarting or
    creating another verifier does not share state; this is an in-memory prototype.
    """

    def __init__(self, task: Task, parameters: Parameters = Parameters(), limit: int = 3):
        self._task = task
        self._parameters = parameters
        self._attempts = Attempts(limit)
        self._session = secrets.token_hex(16)
        self._lock = Lock()
        self._commitments: list[tuple[int, bytes]] = []

    def submit(self, packet: bytes) -> Transcript:
        """Reserve an attempt, freeze and record the commitment, then draw challenges.

        Raise ValueError for malformed inputs or a closed budget. A well-formed
        but invalid result returns an unsuccessful transcript.
        """
        with self._lock:
            attempt = self._attempts.reserve()
            committed = parse(self._task, packet)
            self._commitments.append((attempt, committed.digest))
            challenges = sample(self._task.dimension, self._parameters)
            transcript = record(self._task, committed, self._session, attempt,
                                self._attempts.limit, self._parameters, challenges)
            self._attempts.awarded = transcript.accepted
            return transcript
