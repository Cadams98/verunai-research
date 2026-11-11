"""Run local UW-1 benchmarks and bounded, opt-in correctness experiments."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
from statistics import median
from time import perf_counter_ns
import tracemalloc
from typing import Callable

from .challenge import Parameters
from .commitment import DIGEST_SIZE, HEADER_SIZE, UPDATE_BOUND, encode
from .evaluation import evaluate_steps
from .experiments import adversarial, honest_trials
from .prover import canonical_prover, optimized_prover
from .task import DIMENSIONS, make_task
from .verifier import Verifier


def measure(prepare: Callable[[], Callable], repeats: int) -> dict:
    """Warm once, time fresh fixtures, then trace a separate memory sample."""
    prepare()()
    samples = []
    for _ in range(repeats):
        operation = prepare()
        start = perf_counter_ns()
        operation()
        samples.append(perf_counter_ns() - start)
    operation = prepare()
    tracemalloc.start()
    try:
        operation()
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    middle = median(samples)
    return dict(samples_ns=samples, median_ns=middle, min_ns=min(samples),
                max_ns=max(samples), mad_ns=median(abs(n - middle) for n in samples),
                peak_traced_bytes=peak)


def _reject(verifier: Verifier, payload: bytes) -> None:
    try:
        verifier.submit(payload)
    except ValueError:
        return
    raise RuntimeError("malformed input accepted")


def _verify(verifier: Verifier, payload: bytes) -> None:
    if not verifier.submit(payload).accepted:
        raise RuntimeError("honest packet rejected")


def benchmark(repeats: int) -> dict:
    """Measure full local verification against comparable exact CPU provers."""
    results = {}
    for d in DIMENSIONS:
        task = make_task(d, "benchmark", "local", "0" * 64, 2026)
        result = canonical_prover(task)
        if result != optimized_prover(task):
            raise RuntimeError("prover mismatch")
        packet = encode(task, result)
        cells = (len(packet) - HEADER_SIZE - DIGEST_SIZE) // 4
        dense_body = packet[:HEADER_SIZE] + (1000).to_bytes(4, "big") * cells
        dense_bad_digest = dense_body + bytes(DIGEST_SIZE)
        overflow_body = dense_body[:-4] + (UPDATE_BOUND + 1).to_bytes(4, "big")
        dense_bad_bounds = overflow_body + sha256(overflow_body).digest()
        metrics = {
            "canonical": measure(lambda: lambda: canonical_prover(task), repeats),
            "optimized": measure(lambda: lambda: optimized_prover(task), repeats),
            "submission_encoding": measure(lambda: lambda: encode(task, result), repeats),
            "verifier": measure(lambda: lambda v=Verifier(task): _verify(v, packet), repeats),
            "malformed_short": measure(lambda: lambda v=Verifier(task), p=packet[:-1]: _reject(v, p), repeats),
            "malformed_digest": measure(
                lambda: lambda v=Verifier(task), p=packet[:-1] + bytes([packet[-1] ^ 1]): _reject(v, p),
                repeats),
            "malformed_dense_digest": measure(
                lambda: lambda v=Verifier(task): _reject(v, dense_bad_digest), repeats),
            "malformed_dense_bounds": measure(
                lambda: lambda v=Verifier(task): _reject(v, dense_bad_bounds), repeats),
        }
        verify = metrics["verifier"]["median_ns"]
        prove = metrics["canonical"]["median_ns"]
        optimized = metrics["optimized"]["median_ns"]
        malformed = max(metrics[key]["median_ns"] for key in metrics if key.startswith("malformed_"))
        results[d] = dict(metrics=metrics, submission_bytes=len(packet),
                          packet_sha256=sha256(packet).hexdigest(), precomputation_ns=0,
                          verifier_over_canonical=verify / prove, verifier_over_optimized=verify / optimized,
                          malformed_over_canonical=malformed / prove,
                          malformed_over_optimized=malformed / optimized)
    return dict(repeats=repeats, warmups_per_workload=1, parameters=[32, 2],
                dimensions=results, usefulness=evaluate_steps())


def main() -> None:
    """Write one complete JSON report, leaving previous output intact on interruption."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("benchmark", "honest", "adversarial"), default="benchmark")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--trials", type=int, default=1000)
    parser.add_argument("--dimension", type=int, choices=DIMENSIONS, action="append",
                        help="select honest-mode dimensions (default: all)")
    args = parser.parse_args()
    if args.dimension and args.mode != "honest":
        parser.error("--dimension applies only to honest mode")
    if not 10 <= args.repeats <= 100 or not 1000 <= args.trials <= 10_000:
        parser.error("repeats must be 10..100 and trials 1000..10000")
    if args.mode == "benchmark":
        result = benchmark(args.repeats)
    elif args.mode == "adversarial":
        result = adversarial(args.trials)
    else:
        result = honest_trials(args.trials, tuple(dict.fromkeys(args.dimension or DIMENSIONS)))
    report = dict(mode=args.mode, python=platform.python_version(), os=platform.platform(),
                  cpu=platform.processor(), logical_cpus=os.cpu_count(), backend="CPython exact integers",
                  gpu="not measured; no GPU backend selected", result=result)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)


if __name__ == "__main__":
    main()
