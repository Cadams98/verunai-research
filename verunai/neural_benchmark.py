"""Measure research neural mining and full-step validation (no coin valuation)."""
from __future__ import annotations
import hashlib
import json
import statistics
from time import perf_counter

from .neural_consensus import NeuralChain, neural_candidate


def benchmark_neural(attempts: int = 150, verify_samples: int = 20,
                     backend: str = "python") -> dict:
    if not 4 <= attempts <= 100000 or not 1 <= verify_samples <= 500:
        raise ValueError("attempts=4..100000 and verify_samples=1..500")
    if backend not in ("python", "torch-cpu", "torch-cuda"):
        raise ValueError("Invalid backend")
    chain = NeuralChain(1)
    genesis_loss = chain.training_loss()

    # Warm up backend, then explicitly check that it returns the same block.
    gold = neural_candidate(1, chain.head, "benchmark", 0, 1, chain.weights, "python")
    actual = neural_candidate(1, chain.head, "benchmark", 0, 1, chain.weights, backend)
    if gold != actual:
        raise AssertionError("Backend disagrees with integer consensus; mining unsafe")

    start = perf_counter()
    for nonce in range(attempts):
        neural_candidate(1, chain.head, "benchmark", nonce, 1, chain.weights, backend)
    elapsed = perf_counter() - start

    # A deliberately invalid hash-only shortcut as a cost-control baseline.
    # It cannot earn rewards; it never produces the expected gradient/model.
    start_hash = perf_counter()
    for nonce in range(attempts):
        hashlib.sha256(json.dumps(["unverified", nonce]).encode()).digest()
    hash_elapsed = perf_counter() - start_hash

    winning_nonce = 0
    while True:
        winner = neural_candidate(1, chain.head, "benchmark", winning_nonce, 1, chain.weights)
        if winner.hash.startswith("0"):
            break
        winning_nonce += 1
    times = []
    for _ in range(verify_samples):
        fresh = NeuralChain(1)
        start_verification = perf_counter()
        fresh.accept(winner)
        times.append(perf_counter() - start_verification)
    chain.accept(winner)
    return {
        "protocol": "neural-v2",
        "backend": backend,
        "candidate_attempts": attempts,
        "candidate_seconds": round(elapsed, 6),
        "candidates_per_second": round(attempts / elapsed, 2),
        "hash_only_operations_per_second": round(attempts / max(hash_elapsed, 1e-12), 2),
        "independent_full_replay_verifications": verify_samples,
        "median_verification_milliseconds": round(statistics.median(times) * 1000, 4),
        "starting_model_mse": genesis_loss,
        "accepted_block_model_mse": chain.training_loss(),
        "backend_matches_integer_reference": True,
        "warning": "Hash-only timing is INVALID WORK, not a successful attack. Validation recomputes the whole neural step; this is NOT succinct Proof of Useful Work.",
    }
