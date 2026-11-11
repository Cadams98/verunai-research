"""Canonical verifier records and deterministic replay with a trusted digest."""
from dataclasses import dataclass, replace
from hashlib import sha256
from hmac import compare_digest
import json
import re

from .challenge import Parameters, Vector, Round, check
from .commitment import parse, Commitment
from .task import Task, canonical


@dataclass(frozen=True)
class Transcript:
    """Immutable record for a parsed submission; malformed packets get no record."""
    context: str
    commitment: str
    session: str
    attempt: int
    limit: int
    parameters: Parameters
    challenges: tuple[Vector, ...]
    projections: tuple[Round, ...]
    exact_update: bool
    accepted: bool
    reward_eligible: bool
    digest: str = ""

    def body(self) -> bytes:
        """Encode the transcript fields covered by the digest."""
        return canonical(["UW1/transcript/v1", self.context, self.commitment, self.session,
                          self.attempt, self.limit, self.parameters.bits, self.parameters.rounds,
                          self.challenges, self.projections, self.exact_update, self.accepted,
                          self.reward_eligible])

    def to_bytes(self) -> bytes:
        """Export canonical transcript body followed by its hex digest and newline."""
        return self.body() + b"\n" + self.digest.encode("ascii") + b"\n"


    @classmethod
    def from_bytes(cls, raw: bytes) -> "Transcript":
        """Decode a bounded canonical export; call replay to validate its contents."""
        if type(raw) is not bytes or len(raw) > 100_000:
            raise ValueError("invalid transcript size or type")
        try:
            body, digest, end = raw.split(b"\n")
            if end or not re.fullmatch(rb"[0-9a-f]{64}", digest):
                raise ValueError("invalid transcript framing")
            (domain, context, commitment, session, attempt, limit, bits, rounds,
             vectors, projections, exact, accepted, reward) = json.loads(body)
            if domain != "UW1/transcript/v1":
                raise ValueError("invalid transcript domain")
            result = cls(context, commitment, session, attempt, limit, Parameters(bits, rounds),
                         tuple(tuple(v) for v in vectors),
                         tuple(tuple(tuple(v) for v in row) for row in projections),
                         exact, accepted, reward, digest.decode("ascii"))
            if result.to_bytes() != raw:
                raise ValueError("noncanonical transcript")
            return result
        except (ValueError, TypeError, RecursionError) as exc:
            raise ValueError("invalid transcript encoding") from exc


def record(task: Task, commitment: Commitment, session: str, attempt: int, limit: int,
           params: Parameters, vectors: tuple[Vector, ...]) -> Transcript:
    """Compute projections and construct a digest-bound transcript."""
    accepted, rounds, exact_update = check(task, commitment.result, params, vectors)
    transcript = Transcript(task.context.decode("ascii"), commitment.digest.hex(), session,
                            attempt, limit, params, vectors, rounds, exact_update, accepted, accepted)
    return replace(transcript, digest=sha256(transcript.body()).hexdigest())


def replay(task: Task, packet: bytes, transcript: Transcript, trusted_digest: str) -> bool:
    """Return the recorded decision after replay, or raise on inconsistency.

    The original digest must come from an independent trusted record. Replay
    checks the math and fields, not whether randomness was honestly generated.
    """
    if (type(trusted_digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", trusted_digest)
            or type(transcript.digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", transcript.digest)
            or not compare_digest(trusted_digest, transcript.digest)):
        raise ValueError("trusted transcript digest mismatch")
    if (type(transcript.attempt) is not int or type(transcript.limit) is not int or
            not 1 <= transcript.attempt <= transcript.limit <= 10_000 or
            type(transcript.session) is not str or not re.fullmatch(r"[0-9a-f]{32}", transcript.session)
            or type(transcript.parameters) is not Parameters):
        raise ValueError("invalid attempt metadata")
    expected = record(task, parse(task, packet), transcript.session, transcript.attempt,
                      transcript.limit, transcript.parameters, transcript.challenges)
    if not compare_digest(expected.digest, trusted_digest) or transcript.body() != expected.body():
        raise ValueError("transcript replay mismatch")
    return expected.accepted
