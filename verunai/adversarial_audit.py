"""Demonstrate cost asymmetry of valid and false neural training block headers.

This is a research warning about an UNSOLVED denial-of-service vector.
"""
from __future__ import annotations

from dataclasses import replace
from time import perf_counter

from .core import canonical_bytes, sha256, REWARD
from .neural_v3 import DOMAIN, LedgerBlock, LedgerChain, ledger_candidate
from .wallet import Wallet


def audit_work_asymmetry(samples: int = 50) -> dict:
    if type(samples) is not int or not 5 <= samples <= 250:
        raise ValueError("samples must be 5..250")
    chain = LedgerChain(1)
    miner = Wallet.generate().address
    start = perf_counter()
    for nonce in range(samples):
        _ = ledger_candidate(1, chain.head, miner, nonce, 1, chain.weights)
    honest_s = perf_counter() - start
    forged = []
    start = perf_counter()
    nonce = 0
    while len(forged) < samples:
        draft = LedgerBlock(1, chain.head, miner, nonce, 1, REWARD,
                            "0" * 64, "0" * 64, (), "")
        forged_hash = sha256(canonical_bytes(draft.payload()))
        nonce += 1
        if forged_hash.startswith("0"):
            forged.append(replace(draft, hash=forged_hash))
    fake_header_s = perf_counter() - start
    start = perf_counter()
    rejected = 0
    for fake in forged:
        try:
            chain.accept(fake)
        except ValueError as exc:
            if "Invalid neural training work" not in str(exc):
                raise RuntimeError("Unexpected reject reason") from exc
            rejected += 1
    validation_s = perf_counter() - start
    assert len(chain.blocks) == 0 and rejected == samples
    return {"samples": samples, "fake_headers_rejected": rejected,
            "candidate_compute_seconds_per": round(honest_s / samples, 7),
            "cheap_fake_header_seconds_per": round(fake_header_s / samples, 7),
            "false_header_validation_seconds_per": round(validation_s / samples, 7),
            "network": "none; CPU-local benchmark",
            "finding": "Invalid headers can satisfy hash difficulty without authentic AI work, forcing nodes to recompute work to reject them.",
            "interpretation": "Proof of useful work remains UNSOLVED. CPU timings are platform-dependent and do not establish economic security."}
