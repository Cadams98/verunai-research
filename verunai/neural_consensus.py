"""EXPERIMENTAL v2: integer-exact neural *linear-layer* training bound to blocks.

Each candidate performs a minibatch gradient computation for a trainable
single-layer text prediction model, including two dense matrix multiplies.
Validators independently redo the winning step using Python integer math.

This does NOT establish proof of useful work: candidate gradients may be
precomputed, approximated, or replaced with shortcuts; finding valid blocks
is still a SHA-256 lottery. Verification repeats the complete training step.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from .core import TRAINING_TEXT, REWARD, GENESIS_HASH, canonical_bytes, sha256

VERSION = 2
NETWORK_ID = "verunai-private-neural-experiment-v2"
DIM = 16
BATCH = 64
TARGET_SCALE = 24
UPDATE_DIVISOR = 192
MAX_NONCE = (1 << 64) - 1
# Domain separation prevents v1 block-hash collisions and cross-protocol replay.
DOMAIN = "verunai-neural-integer-training-v2"


def _feature(prev: str, curr: str) -> tuple[int, ...]:
    # Dense signed 'context embedding'; deterministic across architectures.
    digest = hashlib.sha256(f"{DOMAIN}|{ord(prev)}|{ord(curr)}".encode()).digest()
    return tuple(1 if (digest[k] & 1) else -1 for k in range(DIM))

# This deterministic mini corpus is included in project source. The targets
# are character buckets, not meaningful general-purpose language understanding.
_DATA = tuple((
    _feature(TRAINING_TEXT[i], TRAINING_TEXT[i + 1]),
    ord(TRAINING_TEXT[i + 2]) % DIM,
) for i in range(len(TRAINING_TEXT) - 2))


def seed_batch(parent: str, miner: str, nonce: int) -> tuple[list[list[int]], list[list[int]]]:
    """Choose text examples from public data, tied to previous hash + nonce."""
    if not isinstance(nonce, int) or isinstance(nonce, bool) or not 0 <= nonce <= MAX_NONCE:
        raise ValueError("nonce outside unsigned 64-bit range")
    if not isinstance(parent, str) or not re.fullmatch(r"[0-9a-f]{64}", parent):
        raise ValueError("parent must be lower-case SHA-256 hex")
    if not isinstance(miner, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", miner):
        raise ValueError("invalid miner ID")
    seed = bytes.fromhex(sha256(canonical_bytes([DOMAIN, parent, miner, nonce])))
    start = int.from_bytes(seed[:8], "big") % len(_DATA)
    stride = 1 + int.from_bytes(seed[8:16], "big") % (len(_DATA) - 1)
    xs, ys = [], []
    for i in range(BATCH):
        features, cls = _DATA[(start + i * stride) % len(_DATA)]
        xs.append(list(features))
        target = [0] * DIM
        target[cls] = TARGET_SCALE
        ys.append(target)
    return xs, ys


def weights_digest(weights: list[list[int]]) -> str:
    return sha256(canonical_bytes(weights))


def _trunc_div(a: int, divisor: int) -> int:
    # Defined for negative numbers (Python // floors; we need toward-zero).
    return a // divisor if a >= 0 else -((-a) // divisor)


def integer_step(weights: list[list[int]], xs: list[list[int]], ys: list[list[int]]) -> tuple[list[list[int]], str]:
    """Exactly compute Y_hat=XW, grad=X^T(Y_hat-Y), and a quantized step.

    Integer arithmetic is used so independent validators don't need GPU/BLAS.
    No gradients or matrices supplied by a miner are trusted.
    """
    if len(weights) != DIM or any(len(row) != DIM for row in weights):
        raise ValueError("bad weight matrix")
    if len(xs) != BATCH or len(ys) != BATCH:
        raise ValueError("bad batch")
    # X @ W, followed by error to the public targets.
    errors = [[sum(xs[k][i] * weights[i][j] for i in range(DIM)) - ys[k][j]
               for j in range(DIM)] for k in range(BATCH)]
    # X^T @ error; integer-exact SGD gradient.
    gradient = [[sum(xs[k][i] * errors[k][j] for k in range(BATCH))
                 for j in range(DIM)] for i in range(DIM)]
    next_weights = [[weights[i][j] - _trunc_div(gradient[i][j], UPDATE_DIVISOR)
                     for j in range(DIM)] for i in range(DIM)]
    # Bounds keep torch.float32 exactness check safe and make DoS detectable.
    if any(abs(v) > 10_000 for row in next_weights for v in row):
        raise ValueError("model weights exceeded research bounds")
    return next_weights, sha256(canonical_bytes(gradient))


def torch_step(weights: list[list[int]], xs: list[list[int]], ys: list[list[int]], device: str = "cpu") -> tuple[list[list[int]], str]:
    """Optional GPU candidate engine, CPU validation remains authoritative.

    All inputs and intermediate sums are small exact integers represented as
    float64. CUDA uses torch matmul; a mining candidate is only accepted if its
    result matches canonical Python integer output. This is an experiment,
    not a promise that GPU is faster for small matrices.
    """
    try:
        import torch
    except ImportError as e:
        raise RuntimeError("Install PyTorch to use the torch compute backend") from e
    if device not in ("cpu", "cuda"):
        raise ValueError("device must be cpu or cuda")
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable in this PyTorch installation")
    x = torch.tensor(xs, dtype=torch.float64, device=device)
    y = torch.tensor(ys, dtype=torch.float64, device=device)
    w = torch.tensor(weights, dtype=torch.float64, device=device)
    gradient_tensor = x.T @ (x @ w - y)
    gradient = gradient_tensor.to("cpu").to(dtype=torch.int64).tolist()
    next_weights = [[weights[i][j] - _trunc_div(gradient[i][j], UPDATE_DIVISOR)
                     for j in range(DIM)] for i in range(DIM)]
    if any(abs(v) > 10_000 for row in next_weights for v in row):
        raise ValueError("model weights exceeded research bounds")
    return next_weights, sha256(canonical_bytes(gradient))


def compute_step(weights: list[list[int]], parent: str, miner: str, nonce: int,
                 backend: str = "python") -> tuple[list[list[int]], str]:
    xs, ys = seed_batch(parent, miner, nonce)
    if backend == "python":
        return integer_step(weights, xs, ys)
    if backend in ("torch-cpu", "torch-cuda"):
        return torch_step(weights, xs, ys, device="cuda" if backend == "torch-cuda" else "cpu")
    raise ValueError("backend must be python, torch-cpu or torch-cuda")


def evaluation_mse(weights: list[list[int]]) -> float:
    """Full public dataset squared error (in-sample; not general intelligence)."""
    loss = 0
    for x, cls in _DATA:
        for j in range(DIM):
            pred = sum(x[i] * weights[i][j] for i in range(DIM))
            diff = pred - (TARGET_SCALE if j == cls else 0)
            loss += diff * diff
    return round(loss / (len(_DATA) * DIM), 6)


@dataclass(frozen=True)
class NeuralBlock:
    height: int
    prev_hash: str
    miner: str
    nonce: int
    difficulty: int
    reward: int
    gradient_digest: str
    model_digest: str
    hash: str

    def payload(self) -> dict:
        return {"version": VERSION, "domain": DOMAIN, "height": self.height,
                "prev_hash": self.prev_hash, "miner": self.miner,
                "nonce": self.nonce, "difficulty": self.difficulty,
                "reward": self.reward, "gradient_digest": self.gradient_digest,
                "model_digest": self.model_digest}

    def to_dict(self) -> dict:
        return {**self.payload(), "hash": self.hash}

    @classmethod
    def from_dict(cls, obj: dict) -> "NeuralBlock":
        if not isinstance(obj, dict) or obj.get("version") != VERSION or obj.get("domain") != DOMAIN:
            raise ValueError("Wrong neural protocol version or domain")
        return cls(height=obj["height"], prev_hash=obj["prev_hash"], miner=obj["miner"],
                   nonce=obj["nonce"], difficulty=obj["difficulty"], reward=obj["reward"],
                   gradient_digest=obj["gradient_digest"], model_digest=obj["model_digest"],
                   hash=obj["hash"])


def neural_candidate(height: int, prev_hash: str, miner: str, nonce: int,
                     difficulty: int, weights: list[list[int]], backend: str = "python") -> NeuralBlock:
    next_weights, grad_digest = compute_step(weights, prev_hash, miner, nonce, backend)
    draft = NeuralBlock(height, prev_hash, miner, nonce, difficulty, REWARD,
                        grad_digest, weights_digest(next_weights), "")
    return NeuralBlock(height, prev_hash, miner, nonce, difficulty, REWARD,
                       grad_digest, weights_digest(next_weights),
                       sha256(canonical_bytes(draft.payload())))


class NeuralChain:
    def __init__(self, difficulty: int = 1):
        if type(difficulty) is not int or not 1 <= difficulty <= 5:
            raise ValueError("Research difficulty must be 1..5")
        self.difficulty = difficulty
        self.blocks: list[NeuralBlock] = []
        self.weights = [[0] * DIM for _ in range(DIM)]
        self.balances: dict[str, int] = {}

    @property
    def head(self) -> str:
        return self.blocks[-1].hash if self.blocks else GENESIS_HASH

    def accept(self, block: NeuralBlock) -> None:
        if type(block.height) is not int or block.height != len(self.blocks) + 1:
            raise ValueError("Bad neural block height")
        if block.prev_hash != self.head:
            raise ValueError("Bad neural block parent")
        if type(block.difficulty) is not int or block.difficulty != self.difficulty:
            raise ValueError("Wrong neural difficulty")
        if type(block.reward) is not int or block.reward != REWARD:
            raise ValueError("Wrong neural reward")
        if not isinstance(block.hash, str) or not re.fullmatch(r"[0-9a-f]{64}", block.hash):
            raise ValueError("Bad neural hash format")
        # Independently recompute the entire gradient, not just an untrusted digest.
        next_weights, expected_grad = compute_step(self.weights, block.prev_hash,
                                                    block.miner, block.nonce)
        if block.gradient_digest != expected_grad or block.model_digest != weights_digest(next_weights):
            raise ValueError("Neural training work invalid")
        if sha256(canonical_bytes(block.payload())) != block.hash:
            raise ValueError("Tampered neural block hash")
        if not block.hash.startswith("0" * self.difficulty):
            raise ValueError("Neural block difficulty target not met")
        self.blocks.append(block)
        self.weights = next_weights
        self.balances[block.miner] = self.balances.get(block.miner, 0) + REWARD

    def training_loss(self) -> float:
        return evaluation_mse(self.weights)

    def export(self) -> dict:
        return {"protocol_version": VERSION, "mode": "neural-v2", "domain": DOMAIN,
                "difficulty": self.difficulty, "blocks": [b.to_dict() for b in self.blocks]}

    @classmethod
    def import_and_verify(cls, data: dict) -> "NeuralChain":
        if (not isinstance(data, dict) or data.get("protocol_version") != VERSION or
                data.get("mode") != "neural-v2" or data.get("domain") != DOMAIN or
                not isinstance(data.get("blocks"), list)):
            raise ValueError("Wrong neural chain protocol, mode, or domain")
        chain = cls(data["difficulty"])
        if len(data["blocks"]) > 3000:
            raise ValueError("Neural chain length limit exceeded")
        for entry in data["blocks"]:
            chain.accept(NeuralBlock.from_dict(entry))
        return chain


def mine_neural(chain: NeuralChain, miners: dict[str, int], max_attempts: int = 100_000,
                backend: str = "python") -> tuple[NeuralBlock, int]:
    if not miners or any(not isinstance(k, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", k)
                         or type(v) is not int or not 1 <= v <= 100 for k, v in miners.items()):
        raise ValueError("Invalid miners or weights")
    count, nonces = 0, {name: 0 for name in miners}
    while count < max_attempts:
        for name, power in miners.items():
            for _ in range(power):
                nonce = nonces[name]
                nonces[name] += 1
                block = neural_candidate(len(chain.blocks) + 1, chain.head, name, nonce,
                                         chain.difficulty, chain.weights, backend)
                count += 1
                if block.hash.startswith("0" * chain.difficulty):
                    chain.accept(block)
                    return block, count
                if count >= max_attempts:
                    break
    raise RuntimeError("No neural work block found")
