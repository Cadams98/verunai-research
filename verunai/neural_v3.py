"""Research neural-v3: deterministic AI training + signed TEST transfers.

This makes an independently verifiable educational *ledger*, not a secure
coin. It inherits the core experimental PoW weakness: validators rerun the
AI computation and mining rewards are still a SHA-256 lottery.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .core import REWARD, GENESIS_HASH, canonical_bytes, sha256
from .neural_consensus import compute_step, weights_digest, evaluation_mse, DIM, MAX_NONCE
from .wallet import Transfer, ADDRESS_RE, MAX_AMOUNT

VERSION = 3
DOMAIN = "verunai-v3-signed-ledger-neural-work-research"
NETWORK_ID = "verunai-private-neural-v3-signed-ledger"
MAX_TXS = 16
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class LedgerBlock:
    height: int
    prev_hash: str
    miner: str
    nonce: int
    difficulty: int
    reward: int
    gradient_digest: str
    model_digest: str
    transfers: tuple[Transfer, ...]
    hash: str

    def payload(self) -> dict:
        return {"version": VERSION, "domain": DOMAIN, "height": self.height,
                "prev_hash": self.prev_hash, "miner": self.miner, "nonce": self.nonce,
                "difficulty": self.difficulty, "reward": self.reward,
                "gradient_digest": self.gradient_digest, "model_digest": self.model_digest,
                "transfers": [tx.to_dict() for tx in self.transfers]}

    def to_dict(self) -> dict:
        return {**self.payload(), "hash": self.hash}

    @classmethod
    def from_dict(cls, obj: dict) -> "LedgerBlock":
        if not isinstance(obj, dict) or set(obj) != {"version", "domain", "height", "prev_hash", "miner", "nonce", "difficulty", "reward", "gradient_digest", "model_digest", "transfers", "hash"}:
            raise ValueError("Invalid neural-v3 block fields")
        if obj["version"] != VERSION or obj["domain"] != DOMAIN:
            raise ValueError("Wrong neural-v3 protocol")
        txs = obj["transfers"]
        if not isinstance(txs, list) or len(txs) > MAX_TXS:
            raise ValueError("Too many or malformed transfers")
        return cls(obj["height"], obj["prev_hash"], obj["miner"], obj["nonce"],
                   obj["difficulty"], obj["reward"], obj["gradient_digest"],
                   obj["model_digest"], tuple(Transfer.from_dict(t) for t in txs), obj["hash"])


def ledger_candidate(height: int, prev_hash: str, miner: str, nonce: int,
                     difficulty: int, weights: list[list[int]], transfers: Iterable[Transfer] = (),
                     backend: str = "python") -> LedgerBlock:
    if not isinstance(miner, str) or not ADDRESS_RE.fullmatch(miner):
        raise ValueError("Invalid miner reward address")
    txs = tuple(transfers)
    if len(txs) > MAX_TXS:
        raise ValueError("Too many transfers")
    next_weights, grad_digest = compute_step(weights, prev_hash, miner, nonce, backend)
    draft = LedgerBlock(height, prev_hash, miner, nonce, difficulty, REWARD,
                        grad_digest, weights_digest(next_weights), txs, "")
    return LedgerBlock(height, prev_hash, miner, nonce, difficulty, REWARD,
                       grad_digest, weights_digest(next_weights), txs,
                       sha256(canonical_bytes(draft.payload())))


class LedgerChain:
    def __init__(self, difficulty: int = 1):
        if type(difficulty) is not int or not 1 <= difficulty <= 5:
            raise ValueError("Research difficulty must be 1..5")
        self.difficulty = difficulty
        self.blocks: list[LedgerBlock] = []
        self.weights = [[0] * DIM for _ in range(DIM)]
        self.balances: dict[str, int] = {}
        self.sequences: dict[str, int] = {}
        self.included_txids: set[str] = set()

    @property
    def head(self) -> str:
        return self.blocks[-1].hash if self.blocks else GENESIS_HASH

    def check_transfers(self, txs: Iterable[Transfer]) -> tuple[dict[str, int], dict[str, int], set[str], int]:
        """Transactional simulation; no state changes unless entire block passes."""
        result = dict(self.balances)
        sequences = dict(self.sequences)
        seen = set(self.included_txids)
        fees = 0
        for tx in txs:
            if not isinstance(tx, Transfer):
                raise ValueError("Invalid transfer object")
            tx.verify()
            sender = tx.sender
            if tx.txid in seen:
                raise ValueError("Replay or duplicate transfer")
            if tx.sequence != sequences.get(sender, 0):
                raise ValueError("Wrong sender sequence")
            if result.get(sender, 0) < tx.amount + tx.fee:
                raise ValueError("Insufficient sender balance")
            result[sender] -= tx.amount + tx.fee
            result[tx.recipient] = result.get(tx.recipient, 0) + tx.amount
            sequences[sender] = tx.sequence + 1
            seen.add(tx.txid)
            fees += tx.fee
        return result, sequences, seen, fees

    def accept(self, block: LedgerBlock) -> None:
        # Structural and hash/difficulty tests must precede expensive model work.
        if type(block.height) is not int or block.height != len(self.blocks) + 1:
            raise ValueError("Bad height")
        if not isinstance(block.prev_hash, str) or block.prev_hash != self.head:
            raise ValueError("Bad parent")
        if not isinstance(block.miner, str) or not ADDRESS_RE.fullmatch(block.miner):
            raise ValueError("Bad miner address")
        if type(block.nonce) is not int or not 0 <= block.nonce <= MAX_NONCE:
            raise ValueError("Bad nonce")
        if type(block.difficulty) is not int or block.difficulty != self.difficulty:
            raise ValueError("Bad difficulty")
        if type(block.reward) is not int or block.reward != REWARD:
            raise ValueError("Wrong issuance reward")
        if not isinstance(block.transfers, tuple) or len(block.transfers) > MAX_TXS:
            raise ValueError("Invalid transfers")
        if any(not isinstance(v, str) or not HEX64_RE.fullmatch(v)
               for v in (block.hash, block.gradient_digest, block.model_digest)):
            raise ValueError("Invalid digest format")
        if sha256(canonical_bytes(block.payload())) != block.hash:
            raise ValueError("Tampered block header")
        if not block.hash.startswith("0" * self.difficulty):
            raise ValueError("Mining difficulty not met")
        new_balances, new_sequences, new_ids, fees = self.check_transfers(block.transfers)
        next_weights, gradient_digest = compute_step(self.weights, block.prev_hash, block.miner, block.nonce)
        if block.gradient_digest != gradient_digest or block.model_digest != weights_digest(next_weights):
            raise ValueError("Invalid neural training work")
        new_balances[block.miner] = new_balances.get(block.miner, 0) + REWARD + fees
        self.blocks.append(block)
        self.weights = next_weights
        self.balances = new_balances
        self.sequences = new_sequences
        self.included_txids = new_ids

    def training_loss(self) -> float:
        return evaluation_mse(self.weights)

    def export(self) -> dict:
        return {"protocol_version": VERSION, "mode": "neural-v3", "domain": DOMAIN,
                "difficulty": self.difficulty, "blocks": [b.to_dict() for b in self.blocks]}

    @classmethod
    def import_and_verify(cls, data: dict) -> "LedgerChain":
        if (not isinstance(data, dict) or data.get("protocol_version") != VERSION
            or data.get("mode") != "neural-v3" or data.get("domain") != DOMAIN
            or not isinstance(data.get("blocks"), list) or len(data["blocks"]) > 3_000):
            raise ValueError("Wrong neural-v3 export or oversized chain")
        chain = cls(data["difficulty"])
        for entry in data["blocks"]:
            chain.accept(LedgerBlock.from_dict(entry))
        return chain


def mine_ledger(chain: LedgerChain, miner: str, *, transfers: Iterable[Transfer] = (),
                max_attempts: int = 10_000, backend: str = "python") -> tuple[LedgerBlock, int]:
    txs = tuple(transfers)
    chain.check_transfers(txs)
    for nonce in range(max_attempts):
        block = ledger_candidate(len(chain.blocks) + 1, chain.head, miner, nonce,
                                 chain.difficulty, chain.weights, txs, backend)
        if block.hash.startswith("0" * chain.difficulty):
            chain.accept(block)
            return block, nonce + 1
    raise RuntimeError("No block found")
