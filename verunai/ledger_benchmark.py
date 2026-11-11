"""Measure canonical neural-v3 work on a deterministic, local TEST fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import tracemalloc
from collections.abc import Callable
from time import perf_counter_ns

from .core import canonical_bytes
from .neural_consensus import compute_step
from .neural_v3 import LedgerChain, ledger_candidate, mine_ledger
from .wallet import address_from_public_hex


def _measure(operation: Callable[[], object], repeats: int, count: int = 1) -> dict:
    """Report per-operation wall time and peak traced allocations in a separate pass."""
    operation()
    samples = []
    for _ in range(repeats):
        start = perf_counter_ns()
        operation()
        samples.append((perf_counter_ns() - start) / count / 1_000_000)

    tracemalloc.start()
    try:
        operation()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    median = statistics.median(samples)
    return {
        "operations_per_sample": count,
        "samples_ms_per_operation": samples,
        "median_ms": median,
        "min_ms": min(samples),
        "max_ms": max(samples),
        "median_absolute_deviation_ms": statistics.median(abs(sample - median) for sample in samples),
        "operations_per_second_at_median": 1000 / median,
        "peak_traced_bytes_per_sample": peak,
    }


def benchmark_ledger(attempts: int = 150, repeats: int = 5, blocks: int = 8) -> dict:
    """Measure canonical neural-v3 work using a deterministic empty-block fixture.

    Args:
        attempts: Number of operations per training, candidate, and hash sample.
        repeats: Number of wall-clock samples per workload.
        blocks: Number of blocks to mine for the replay fixture.

    Returns:
        A JSON-serializable report with environment and fixture metadata,
        per-operation timings, throughput, and peak traced Python allocations.

    Raises:
        ValueError: If a control is out of range or allocation tracing is active.
    """
    if not 1 <= attempts <= 10_000 or not 2 <= repeats <= 50 or not 2 <= blocks <= 100:
        raise ValueError("Expected attempts=1..10000, repeats=2..50, blocks=2..100")
    if tracemalloc.is_tracing():
        raise ValueError("Run the benchmark with allocation tracing initially disabled")

    # A syntactically valid TEST reward address requires no private key.
    miner = address_from_public_hex("00" * 32)
    fixture = LedgerChain(1)
    for _ in range(blocks):
        mine_ledger(fixture, miner)
    exported = fixture.export()
    winner = fixture.blocks[0]
    reference = LedgerChain(1)
    # The winning candidate is checked by a fresh canonical validator.
    reference.accept(winner)
    if LedgerChain.import_and_verify(exported).export() != exported:
        raise AssertionError("Fixture failed independent canonical replay")

    def training() -> None:
        for nonce in range(attempts):
            compute_step(fixture.weights, fixture.head, miner, nonce)

    def candidates() -> None:
        for nonce in range(attempts):
            ledger_candidate(blocks + 1, fixture.head, miner, nonce, 1, fixture.weights)

    # Isolate SHA-256 from serialization and model work using canonical payload bytes.
    payload = canonical_bytes(winner.payload())

    def hashing() -> None:
        for _ in range(attempts):
            hashlib.sha256(payload).digest()

    def verify_block() -> None:
        LedgerChain(1).accept(winner)

    replay = {}
    for height in (blocks // 2, blocks):
        prefix = {**exported, "blocks": exported["blocks"][:height]}
        replay[str(height)] = {
            "canonical_json_bytes": len(canonical_bytes(prefix)),
            **_measure(lambda: LedgerChain.import_and_verify(prefix), repeats),
        }

    return {
        "protocol": "neural-v3",
        "backend": "python",
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
        },
        "fixture": {"difficulty": 1, "blocks": blocks, "transfers": 0, "head": fixture.head},
        "repeats": repeats,
        "training_including_batch_and_gradient_digest": _measure(training, repeats, attempts),
        "canonical_candidate": _measure(candidates, repeats, attempts),
        "sha256_preencoded_payload": _measure(hashing, repeats, attempts),
        "verify_genesis_block_including_chain_init": _measure(verify_block, repeats),
        "replay_by_height": replay,
    }


def main() -> None:
    """Read benchmark controls from the command line and print a JSON report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts", type=int, default=150)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--blocks", type=int, default=8)
    args = parser.parse_args()
    try:
        report = benchmark_ledger(args.attempts, args.repeats, args.blocks)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
