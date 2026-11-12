"""Commit, draw a beacon, reveal, then score each update on fresh evaluation data.

One round:
    1. The coordinator announces the round number and the current model digest.
    2. Each worker sends a *commitment*: a hash binding the round, the model
       digest, its identity, its update and a secret salt.
    3. After commitments close, the coordinator draws a random *beacon*.
    4. Workers reveal their update and salt. A reveal that does not match its
       commitment is refused.
    5. Reveals are processed in an order derived from the beacon. Each update is
       scored against the *current* model on its own fresh evaluation batch
       derived from the beacon and the commitment. An update is applied only if
       the exact sign test shows improvement. Its score is its net wins.

Trusted in this prototype: the coordinator (ordering, beacon, bookkeeping) and
the data oracle (fresh labelled examples). Worker identities are labels. The
"score" is a number in a local record and has no monetary or consensus role.

Not provided: authenticated workers, persistent state across coordinator
instances, a signed or append-only settlement history, any limit on
submissions, or secrecy of evaluation data from someone who knows the oracle
seed. A commitment binds its round number, model fingerprint and worker label,
which stops reuse inside one ``Round``; nothing here prevents a restarted or
second coordinator from accepting the same material again.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from hashlib import sha256
from typing import Callable

from .data import Oracle
from .model import Weights, add, correct, decode, digest, encode
from .stats import DEFAULT_ALPHA, Alpha, improved

WORKER_ID_LIMIT = 64


def commitment(round_number: int, model_digest: str, worker: str, update: bytes, salt: bytes) -> str:
    """Return the hex commitment binding a worker's update to one round and model."""
    body = json.dumps(["UW2/commit/v1", round_number, model_digest, worker,
                       sha256(update).hexdigest(), salt.hex()], separators=(",", ":"))
    return sha256(body.encode("ascii")).hexdigest()


def paired_counts(old: Weights, new: Weights, batch) -> tuple[int, int]:
    """Return (wins, losses) of ``new`` against ``old`` on one evaluation batch."""
    xs, ys = batch
    before, after = correct(old, xs, ys), correct(new, xs, ys)
    wins = sum(1 for b, a in zip(before, after) if a and not b)
    losses = sum(1 for b, a in zip(before, after) if b and not a)
    return wins, losses


@dataclass(frozen=True)
class Settlement:
    """Outcome of one revealed update."""

    worker: str
    commitment: str
    status: str            # accepted | rejected | not_revealed | invalid_update
    wins: int = 0
    losses: int = 0
    score: int = 0         # net wins credited when accepted, else 0


class Round:
    """State machine for one commit-beacon-reveal-settle round.

    Args:
        oracle: Trusted source of fresh evaluation examples.
        weights: Current shared model.
        round_number: Non-negative round counter bound into commitments.
        batch_size: Fresh evaluation examples per update (50..50000).
        alpha: False-acceptance limit of the sign test.
        beacon_source: Callable returning 32 fresh random bytes. The default is
            the system CSPRNG. Tests inject a recorded source for reproducibility.
    """

    def __init__(self, oracle: Oracle, weights: Weights, round_number: int, batch_size: int = 1500,
                 alpha: Alpha = DEFAULT_ALPHA,
                 beacon_source: Callable[[], bytes] = lambda: secrets.token_bytes(32)) -> None:
        if type(round_number) is not int or round_number < 0:
            raise ValueError("round number must be a non-negative integer")
        if type(batch_size) is not int or not 50 <= batch_size <= 50_000:
            raise ValueError("batch size must be 50..50000")
        self._oracle = oracle
        self.weights = weights
        self.round_number = round_number
        self.model_digest = digest(weights)
        self._batch_size = batch_size
        self._alpha = alpha
        self._beacon_source = beacon_source
        self._commitments: dict[str, str] = {}
        self._reveals: dict[str, Weights | None] = {}
        self.beacon: bytes | None = None
        self.settlements: list[Settlement] | None = None

    def commit(self, worker: str, value: str) -> None:
        """Record one commitment per worker; refuse once the beacon exists."""
        if self.beacon is not None:
            raise ValueError("commitments are closed")
        if (type(worker) is not str or not 1 <= len(worker) <= WORKER_ID_LIMIT or
                not worker.isascii() or not worker.replace("-", "").replace("_", "").isalnum()):
            raise ValueError("invalid worker label")
        if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("commitment must be 64 lowercase hex characters")
        if worker in self._commitments:
            raise ValueError("worker already committed this round")
        if value in self._commitments.values():
            raise ValueError("duplicate commitment")
        self._commitments[worker] = value

    def close_commitments(self) -> bytes:
        """Draw the beacon. No commitment can be added or changed afterwards."""
        if self.beacon is not None:
            raise ValueError("beacon already drawn")
        beacon = self._beacon_source()
        if type(beacon) is not bytes or len(beacon) != 32:
            raise RuntimeError("beacon source must return 32 bytes")
        self.beacon = beacon
        return beacon

    def reveal(self, worker: str, update: bytes, salt: bytes) -> bool:
        """Accept a reveal only if it matches the worker's commitment.

        Returns:
            ``True`` if the reveal matched and the update is well formed.
        """
        if self.beacon is None or self.settlements is not None:
            raise ValueError("reveals are accepted only between the beacon and settlement")
        if worker not in self._commitments or worker in self._reveals:
            raise ValueError("no open commitment for this worker")
        if type(update) is not bytes or type(salt) is not bytes or not 16 <= len(salt) <= 64:
            raise ValueError("update and salt must be bytes; salt is 16..64 bytes")
        if commitment(self.round_number, self.model_digest, worker, update, salt) != self._commitments[worker]:
            raise ValueError("reveal does not match the commitment")
        try:
            self._reveals[worker] = decode(update)
        except ValueError:
            self._reveals[worker] = None
            return False
        return True

    def settle(self) -> list[Settlement]:
        """Score every revealed update on its own fresh batch and apply the accepted ones."""
        if self.beacon is None or self.settlements is not None:
            raise ValueError("settlement needs a beacon and runs once")
        order = sorted(self._commitments,
                       key=lambda w: sha256(self.beacon + bytes.fromhex(self._commitments[w])).digest())
        results = []
        for worker in order:
            value = self._commitments[worker]
            if worker not in self._reveals:
                results.append(Settlement(worker, value, "not_revealed"))
                continue
            delta = self._reveals[worker]
            try:
                if delta is None:
                    raise ValueError("malformed update")
                candidate = add(self.weights, delta)
            except ValueError:
                results.append(Settlement(worker, value, "invalid_update"))
                continue
            batch = self._oracle.evaluation_batch(self.beacon, bytes.fromhex(value), self._batch_size)
            wins, losses = paired_counts(self.weights, candidate, batch)
            if improved(wins, losses, self._alpha):
                self.weights = candidate
                results.append(Settlement(worker, value, "accepted", wins, losses, wins - losses))
            else:
                results.append(Settlement(worker, value, "rejected", wins, losses, 0))
        self.settlements = results
        return results

    def record(self) -> dict:
        """Return a JSON-serialisable record of the round's arithmetic outcome.

        The record is unsigned. It is an input to ``recompute_arithmetic``, not
        an authenticated history.
        """
        if self.settlements is None:
            raise ValueError("round is not settled")
        return {"round": self.round_number, "model_before": self.model_digest,
                "model_after": digest(self.weights), "beacon": self.beacon.hex(),
                "batch_size": self._batch_size, "alpha": list(self._alpha),
                "settlements": [vars(s) for s in self.settlements]}


def submit(round_: Round, worker: str, delta: Weights, salt: bytes) -> tuple[bytes, bytes]:
    """Worker-side helper: encode an update and register its commitment."""
    update = encode(delta)
    round_.commit(worker, commitment(round_.round_number, round_.model_digest, worker, update, salt))
    return update, salt


def recompute_arithmetic(record: dict, oracle: Oracle, weights_before: Weights,
                         reveals: dict[str, bytes]) -> bool:
    """Recompute a round's scores and final model from inputs the caller already trusts.

    This is an arithmetic consistency check only. Given a record, the starting
    model, the revealed updates and the oracle, it recomputes each listed
    update's wins, losses, decision and the final model fingerprint.

    It does NOT authenticate anything. It does not check that the beacon was
    drawn after the commitments, that reveals match their commitments, that
    the listed workers or order are genuine, or that the record is the one the
    coordinator produced. A fabricated record that is internally consistent
    passes. It also needs the oracle, whose seed discloses the evaluation data.

    Returns:
        ``True`` if the recomputed settlements and final fingerprint match the record.
    """
    if digest(weights_before) != record["model_before"]:
        return False
    beacon = bytes.fromhex(record["beacon"])
    weights = weights_before
    for item in record["settlements"]:
        expected = Settlement(**item)
        if expected.status in ("not_revealed", "invalid_update"):
            continue
        try:
            candidate = add(weights, decode(reveals[expected.worker]))
        except (KeyError, ValueError):
            return False
        batch = oracle.evaluation_batch(beacon, bytes.fromhex(expected.commitment), record["batch_size"])
        wins, losses = paired_counts(weights, candidate, batch)
        accepted = improved(wins, losses, tuple(record["alpha"]))
        actual = Settlement(expected.worker, expected.commitment,
                            "accepted" if accepted else "rejected", wins, losses,
                            wins - losses if accepted else 0)
        if actual != expected:
            return False
        if accepted:
            weights = candidate
    return digest(weights) == record["model_after"]
