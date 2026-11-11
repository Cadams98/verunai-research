"""CPU baseline for candidate AI-bound hashes and acceptance replay.

This is deliberately NOT a GPU benchmark, mining profitability estimate,
a proof of useful work, or a cryptographic security result.
"""
from __future__ import annotations

import statistics
from time import perf_counter
from .core import Chain, make_candidate


def benchmark(attempts: int = 2000, verify_samples: int = 100) -> dict[str, float | int]:
    if not 1 <= attempts <= 2_000_000:
        raise ValueError("attempts must be 1..2,000,000")
    if not 1 <= verify_samples <= 10000:
        raise ValueError("verify_samples must be 1..10,000")

    chain = Chain(difficulty=1)
    start = perf_counter()
    for nonce in range(attempts):
        make_candidate(1, chain.head, "baseline", nonce, 1)
    elapsed = perf_counter() - start

    # Find a winning block and measure independent replay on *fresh* chains.
    nonce = 0
    winner = make_candidate(1, chain.head, "baseline", nonce, 1)
    while not winner.hash.startswith("0"):
        nonce += 1
        winner = make_candidate(1, chain.head, "baseline", nonce, 1)

    times = []
    for _ in range(verify_samples):
        verifier = Chain(difficulty=1)
        t0 = perf_counter()
        verifier.accept(winner)
        times.append(perf_counter() - t0)

    return {
        "candidate_attempts": attempts,
        "candidate_seconds": round(elapsed, 6),
        "candidates_per_second": round(attempts / max(elapsed, 1e-12), 2),
        "independent_validations": verify_samples,
        "median_validation_milliseconds": round(1000 * statistics.median(times), 4),
        "warning": "Toy CPU baseline only; no useful-work security, GPU speed, or energy claim.",
    }
