"""Run local UW-1 benchmarks and bounded, opt-in correctness experiments."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
from random import Random
from statistics import median
from time import perf_counter_ns, process_time_ns
import tracemalloc
from typing import Callable

from .challenge import Parameters
from .commitment import DIGEST_SIZE, HEADER_SIZE, UPDATE_BOUND, encode
from .evaluation import evaluate_steps
from .experiments import adversarial, honest_trials, perturb, with_gradient
from .prover import canonical_prover, optimized_prover
from .task import DIMENSIONS, GRADIENT_BOUND, RESIDUAL_BOUND, make_task
from .verifier import Verifier


def _batch_cpu(prepare: Callable, wall_ns: float) -> dict | None:
    # Windows CPU clocks can advance in roughly 16 ms increments. Time a batch
    # of fresh operations separately when one invocation is too short.
    if wall_ns >= 20_000_000:
        return None
    count = min(50_000, max(2, int(125_000_000 / max(wall_ns, 1))))
    operations = [prepare() for _ in range(count)]
    start = process_time_ns()
    for operation in operations:
        operation()
    elapsed = process_time_ns() - start
    return dict(operations=count, total_cpu_ns=elapsed,
                cpu_ns_per_operation=elapsed / count if elapsed else None)


def measure(cases: list[dict[str, Callable]], repeats: int) -> dict:
    """Interleave timed cases and trace each fixture in a separate memory pass."""
    names = list(cases[0])
    wall = {name: [] for name in names}
    cpu = {name: [] for name in names}
    peaks = {name: [] for name in names}
    order = []
    rng = Random(2026)
    for case in cases:
        for prepare in case.values():
            prepare()()
    for repeat in range(repeats):
        fixture = repeat % len(cases)
        names_this_round = rng.sample(names, len(names))
        order.append(dict(fixture=fixture, workloads=names_this_round))
        for name in names_this_round:
            operation = cases[fixture][name]()
            start_cpu = process_time_ns()
            start = perf_counter_ns()
            operation()
            wall[name].append(perf_counter_ns() - start)
            cpu[name].append(process_time_ns() - start_cpu)
    for case in cases:
        for name, prepare in case.items():
            operation = prepare()
            tracemalloc.start()
            try:
                operation()
                peaks[name].append(tracemalloc.get_traced_memory()[1])
            finally:
                tracemalloc.stop()
    metrics = {}
    for name, samples in wall.items():
        middle = median(samples)
        metrics[name] = dict(samples_ns=samples, median_ns=middle, min_ns=min(samples),
                             max_ns=max(samples), mad_ns=median(abs(n - middle) for n in samples),
                             cpu_samples_ns=cpu[name], cpu_median_ns=median(cpu[name]),
                             peak_traced_bytes=max(peaks[name]), fixture_peaks_bytes=peaks[name],
                             fixture_median_ns=[median(samples[i::len(cases)])
                                                for i in range(len(cases))])
    for name, metric in metrics.items():
        metric["fixture_batched_cpu"] = [
            _batch_cpu(case[name], wall_ns)
            for case, wall_ns in zip(cases, metric["fixture_median_ns"])
        ]
    return dict(metrics=metrics, order=order)


def _reject(verifier: Verifier, payload: bytes) -> None:
    try:
        verifier.submit(payload)
    except ValueError:
        return
    raise RuntimeError("malformed input accepted")


def _verify(verifier: Verifier, payload: bytes) -> None:
    if not verifier.submit(payload).accepted:
        raise RuntimeError("honest packet rejected")


def _rejected_math(verifier: Verifier, packet: bytes) -> None:
    if verifier.submit(packet).accepted:
        raise RuntimeError("incorrect mathematical result accepted")


def _fixture(d: int, seed: int) -> tuple[dict, dict[str, Callable]]:
    weights = None if seed == 2026 else tuple(
        tuple(((i * 173 + j * 307 + seed) % 20001) - 10000 for j in range(d))
        for i in range(d))
    task = make_task(d, "benchmark", "local", "0" * 64, seed, weights)
    result = canonical_prover(task)
    if result != optimized_prover(task):
        raise RuntimeError("prover mismatch")
    packet = encode(task, result)
    body = packet[:-DIGEST_SIZE]
    cells = (len(body) - HEADER_SIZE) // 4
    dense = (seed * 41).to_bytes(4, "big", signed=True)
    dense_body = packet[:HEADER_SIZE] + dense * cells
    ends = (max(64, d) * d, (max(64, d) + d) * d, cells)
    bounds = (RESIDUAL_BOUND, GRADIENT_BOUND, UPDATE_BOUND)
    malformed_section = seed % len(ends)
    offset = HEADER_SIZE + (ends[malformed_section] - 1) * 4
    value = bounds[malformed_section] + 1
    overflow = (-value if seed % 2 else value).to_bytes(4, "big", signed=True)
    overflow_body = dense_body[:offset] + overflow + dense_body[offset + 4:]
    wrong = with_gradient(task, result, perturb(result.gradient, {(0, 0): 1}))
    wrong_packet = encode(task, wrong)

    def submit(operation: Callable, payload: bytes) -> Callable:
        return lambda: lambda verifier=Verifier(task): operation(verifier, payload)

    workloads = {
        "canonical": lambda: lambda: canonical_prover(task),
        "optimized": lambda: lambda: optimized_prover(task),
        "submission_encoding": lambda: lambda: encode(task, result),
        "verifier": submit(_verify, packet),
        "malformed_short": submit(_reject, packet[:-1]),
        "malformed_oversized": submit(_reject, packet + b"x"),
        "malformed_context": submit(_reject, b"x" + packet[1:]),
        "malformed_digest": submit(_reject, body + packet[-DIGEST_SIZE:-1] + bytes([packet[-1] ^ 1])),
        "malformed_dense_digest": submit(_reject, dense_body + bytes(DIGEST_SIZE)),
        "malformed_dense_bounds": submit(_reject, overflow_body + sha256(overflow_body).digest()),
        "dishonest_math": submit(_rejected_math, wrong_packet),
    }
    metadata = dict(seed=seed, submission_bytes=len(packet), packet_sha256=sha256(packet).hexdigest(),
                    overflow_section=("residual", "gradient", "weights")[malformed_section])
    return metadata, workloads


def benchmark(repeats: int) -> dict:
    """Measure complete verification and rejection on three reproducible fixtures."""
    results = {}
    for d in DIMENSIONS:
        fixtures, cases = zip(*(_fixture(d, seed) for seed in (2026, 2027, 2028)))
        measured = measure(list(cases), repeats)
        metrics = measured["metrics"]
        verify = metrics["verifier"]["median_ns"]
        prove = metrics["canonical"]["median_ns"]
        optimized = metrics["optimized"]["median_ns"]
        malformed = max(max(metric["fixture_median_ns"]) for name, metric in metrics.items()
                        if name.startswith("malformed_"))
        results[d] = dict(**measured, fixtures=fixtures, submission_bytes=fixtures[0]["submission_bytes"],
                          precomputation_ns=0,
                          verifier_over_canonical=verify / prove, verifier_over_optimized=verify / optimized,
                          worst_malformed_fixture_median_ns=malformed,
                          malformed_over_canonical=malformed / prove,
                          malformed_over_optimized=malformed / optimized)
    return dict(repeats=repeats, warmups_per_workload_per_fixture=1, parameters=[32, 2],
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
    parser.add_argument("--workers", type=int, choices=range(1, 17), default=1,
                        help="local processes for honest-mode correctness trials")
    args = parser.parse_args()
    if args.workers != 1 and args.mode != "honest":
        parser.error("--workers applies only to honest mode")
    if args.dimension and args.mode != "honest":
        parser.error("--dimension applies only to honest mode")
    if not 10 <= args.repeats <= 100 or not 1000 <= args.trials <= 10_000:
        parser.error("repeats must be 10..100 and trials 1000..10000")
    if args.mode == "benchmark":
        result = benchmark(args.repeats)
    elif args.mode == "adversarial":
        result = adversarial(args.trials)
    else:
        result = honest_trials(args.trials, tuple(dict.fromkeys(args.dimension or DIMENSIONS)), args.workers)
    report = dict(mode=args.mode, python=platform.python_version(), os=platform.platform(),
                  cpu=platform.processor(), logical_cpus=os.cpu_count(), backend="CPython exact integers",
                  gpu="not measured; no GPU backend selected", workers=args.workers, result=result)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    if args.mode == "honest" and any(item["failures"] for item in result.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
