"""Educational AI-work-bound block mining prototype.

NOT a permissionless, cryptographically secure useful-work consensus protocol.
All nodes must agree on data, Python implementation, and protocol parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Iterable

PROTOCOL_VERSION = 1
ALPHABET = " abcdefghijklmnopqrstuvwxyz.,!?"
CHAR_TO_INDEX = {char: i for i, char in enumerate(ALPHABET)}
VOCAB = len(ALPHABET)
GENESIS_HASH = "0" * 64
BATCH_SIZE = 48
# Original example data. Real deployments must establish a verifiable dataset policy.
TRAINING_TEXT = (
    "miners train a shared model. a useful block improves the model. "
    "the network rewards valid work. the model learns patterns in text. "
    "computers check every block. people contribute computing power. "
    "the miner finds a block and earns a reward. "
) * 10
REWARD = 50  # Fictional test tokens per block; no exchange or wallet.


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def training_batch(prev_hash: str, miner: str, nonce: int) -> tuple[tuple[int, int, int], ...]:
    """Produce a nonce-dependent mini-batch of next-character counts.

    This is a real (very small) character-level statistical language-model
    update, not gradient training of a neural network.
    """
    seed = bytes.fromhex(sha256(canonical_bytes({"prev": prev_hash, "miner": miner, "nonce": nonce})))
    num_pairs = len(TRAINING_TEXT) - 1
    start = int.from_bytes(seed[:8], "big") % num_pairs
    stride = 1 + (int.from_bytes(seed[8:16], "big") % (num_pairs - 1))
    counts: dict[tuple[int, int], int] = {}
    for i in range(BATCH_SIZE):
        position = (start + i * stride) % num_pairs
        a = CHAR_TO_INDEX[TRAINING_TEXT[position]]
        b = CHAR_TO_INDEX[TRAINING_TEXT[position + 1]]
        counts[(a, b)] = counts.get((a, b), 0) + 1
    return tuple((a, b, n) for (a, b), n in sorted(counts.items()))


@dataclass(frozen=True)
class Block:
    height: int
    prev_hash: str
    miner: str
    nonce: int
    difficulty: int
    reward: int
    updates: tuple[tuple[int, int, int], ...]
    hash: str

    def payload(self) -> dict:
        return {
            "version": PROTOCOL_VERSION,
            "height": self.height,
            "prev_hash": self.prev_hash,
            "miner": self.miner,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "reward": self.reward,
            "updates": [list(u) for u in self.updates],
        }

    def to_dict(self) -> dict:
        return {**self.payload(), "hash": self.hash}

    @classmethod
    def from_dict(cls, item: dict) -> "Block":
        if item.get("version") != PROTOCOL_VERSION:
            raise ValueError("Unsupported protocol version")
        return cls(
            height=item["height"], prev_hash=item["prev_hash"],
            miner=item["miner"], nonce=item["nonce"],
            difficulty=item["difficulty"], reward=item["reward"],
            updates=tuple(tuple(t) for t in item["updates"]), hash=item["hash"]
        )


def make_candidate(height: int, prev_hash: str, miner: str, nonce: int, difficulty: int) -> Block:
    updates = training_batch(prev_hash, miner, nonce)
    draft = Block(height, prev_hash, miner, nonce, difficulty, REWARD, updates, "")
    return Block(height, prev_hash, miner, nonce, difficulty, REWARD, updates,
                 sha256(canonical_bytes(draft.payload())))


def blank_model() -> list[list[int]]:
    return [[0] * VOCAB for _ in range(VOCAB)]


class Chain:
    def __init__(self, difficulty: int = 2):
        if not isinstance(difficulty, int) or not 1 <= difficulty <= 5:
            raise ValueError("Demo difficulty must be between 1 and 5")
        self.difficulty = difficulty
        self.blocks: list[Block] = []
        self.counts = blank_model()
        self.balances: dict[str, int] = {}

    @property
    def head(self) -> str:
        return self.blocks[-1].hash if self.blocks else GENESIS_HASH

    def accept(self, block: Block) -> None:
        if block.height != len(self.blocks) + 1:
            raise ValueError("Bad height")
        if block.prev_hash != self.head:
            raise ValueError("Bad parent hash")
        if block.difficulty != self.difficulty:
            raise ValueError("Wrong difficulty")
        if block.reward != REWARD:
            raise ValueError("Wrong issuance reward")
        if not isinstance(block.nonce, int) or block.nonce < 0:
            raise ValueError("Invalid nonce")
        if not isinstance(block.miner, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", block.miner):
            raise ValueError("Invalid miner identifier")
        # Recompute the AI work instead of trusting a miner's asserted output.
        expected = training_batch(block.prev_hash, block.miner, block.nonce)
        if block.updates != expected:
            raise ValueError("AI work verification failed")
        if sha256(canonical_bytes(block.payload())) != block.hash:
            raise ValueError("Tampered block hash")
        if not block.hash.startswith("0" * self.difficulty):
            raise ValueError("Proof-of-work target not met")
        self.blocks.append(block)
        for a, b, n in block.updates:
            self.counts[a][b] += n
        self.balances[block.miner] = self.balances.get(block.miner, 0) + block.reward

    def cross_entropy(self) -> float:
        """Full-corpus next-character cross-entropy with Laplace smoothing."""
        totals = [sum(row) + VOCAB for row in self.counts]
        log_sum = 0.0
        for a_char, b_char in zip(TRAINING_TEXT, TRAINING_TEXT[1:]):
            a, b = CHAR_TO_INDEX[a_char], CHAR_TO_INDEX[b_char]
            log_sum -= math.log((self.counts[a][b] + 1) / totals[a])
        return log_sum / (len(TRAINING_TEXT) - 1)

    def export(self) -> dict:
        return {"protocol_version": PROTOCOL_VERSION, "difficulty": self.difficulty,
                "blocks": [b.to_dict() for b in self.blocks]}

    @classmethod
    def import_and_verify(cls, data: dict) -> "Chain":
        if data.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError("Unsupported export protocol")
        chain = cls(data["difficulty"])
        for payload in data["blocks"]:
            chain.accept(Block.from_dict(payload))
        return chain


def mine_round_robin(chain: Chain, powers: dict[str, int], max_attempts: int = 2_000_000) -> tuple[Block, int]:
    """Simulated miners compete by computing different nonce-dependent ML batches.

    Powers = attempted candidates per simulated round, NOT actual benchmark rates.
    This function does not communicate over a network or use a GPU.
    """
    if not powers or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", name) or
                         not isinstance(power, int) or not 1 <= power <= 100 for name, power in powers.items()):
        raise ValueError("Provide 1-100 positive attempts per round per named miner")
    nonces = {miner: 0 for miner in powers}
    attempts = 0
    while attempts < max_attempts:
        for miner, power in powers.items():
            for _ in range(power):
                nonce = nonces[miner]
                nonces[miner] += 1
                candidate = make_candidate(len(chain.blocks) + 1, chain.head, miner, nonce, chain.difficulty)
                attempts += 1
                if candidate.hash.startswith("0" * chain.difficulty):
                    chain.accept(candidate)
                    return candidate, attempts
                if attempts >= max_attempts:
                    break
    raise RuntimeError("No block found before simulation attempt limit")
