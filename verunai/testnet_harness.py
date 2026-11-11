"""Launch three or more unmodified VERUNAI nodes as separate local processes and audit them.

Phase P0 of the v0.8 private-testnet plan. The harness measures the *existing*
v0.6 node (``python -m verunai node``). It does not change consensus, fork
choice, networking or storage; it only starts processes, watches them and
re-verifies what they saved.

One trial:
    1. Allocate loopback ports and start one byte-counting relay per node.
    2. Start N node processes (full mesh, peers addressed through the relays),
       each with its own temporary directory and storage file.
    3. Poll ``/status`` until every node reports the same head at the target
       height for a stability window, or a deadline passes.
    4. Sample CPU time, peak memory and relay byte counts, then stop all nodes.
    5. Independently re-verify every saved chain twice: in process with the
       protocol's ``import_and_verify`` and in a fresh ``python -m verunai audit``
       process. Compare ledger fingerprints across nodes.

Seeds make trial *configuration* reproducible (miner identities, launch order and
launch delays). Block contents are not reproducible because the existing node
chooses nonce start positions with ``os.urandom``; the harness records outcomes
instead of claiming bit-for-bit replay.

Everything binds to 127.0.0.1. Rewards are fictional TEST units.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

from .core import Chain, canonical_bytes
from .neural_consensus import NeuralChain, weights_digest
from .neural_v3 import LedgerChain
from .process_metrics import launcher_warning, pid_alive, sample_process
from .testnet_proxy import LOOPBACK, CountingRelay
from .wallet import address_from_public_hex

PROTOCOLS = {"bigram-v1": Chain, "neural-v2": NeuralChain, "neural-v3": LedgerChain}
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STATUS_LIMIT_BYTES = 64_000
POLL_INTERVAL = 0.1
STABLE_WINDOW = 1.0
_PROXY_ENVIRONMENT = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy",
                      "all_proxy")
# A direct opener: harness monitoring must never be routed through a configured HTTP proxy.
_DIRECT = build_opener(ProxyHandler({}))


class TrialFailure(Exception):
    """A trial ended without a verified, converged three-node ledger.

    Attributes:
        kind: Short machine-readable failure category.
    """

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind


@dataclass(frozen=True)
class TrialConfig:
    """Reproducible inputs of one trial.

    Attributes:
        seed: Integer from which identities and launch schedule are derived.
        protocol: ``bigram-v1``, ``neural-v2`` or ``neural-v3``.
        nodes: Number of node processes (3..5).
        difficulty: Leading zero hex digits required by every node (1..3).
        target_height: Height at which nodes stop mining (2..50).
        timeout: Seconds allowed from first launch to convergence (5..300).
        sync_interval: Seconds between each node's peer polls.
        use_relays: Route node-to-node traffic through counting relays.
        node_difficulty_overrides: Test hook; per-node difficulty to force divergence.
    """

    seed: int
    protocol: str = "neural-v3"
    nodes: int = 3
    difficulty: int = 2
    target_height: int = 10
    timeout: float = 90.0
    sync_interval: float = 0.2
    use_relays: bool = True
    node_difficulty_overrides: dict = field(default_factory=dict)

    def validate(self) -> None:
        """Raise ``ValueError`` for out-of-range controls."""
        if self.protocol not in PROTOCOLS:
            raise ValueError("protocol must be bigram-v1, neural-v2 or neural-v3")
        if not 3 <= self.nodes <= 5:
            raise ValueError("nodes must be 3..5")
        if not 1 <= self.difficulty <= 3:
            raise ValueError("difficulty must be 1..3")
        if not 2 <= self.target_height <= 50:
            raise ValueError("target_height must be 2..50")
        if not 5 <= self.timeout <= 300:
            raise ValueError("timeout must be 5..300 seconds")
        if not 0.05 <= self.sync_interval <= 5:
            raise ValueError("sync_interval must be 0.05..5 seconds")
        if not 0 <= self.seed < 2**63:
            raise ValueError("seed must be 0..2**63-1")
        for index, value in self.node_difficulty_overrides.items():
            if not 0 <= int(index) < self.nodes or not 1 <= int(value) <= 3:
                raise ValueError("difficulty override must name a node index and difficulty 1..3")


@dataclass(frozen=True)
class LaunchPlan:
    """Seed-derived node identities and launch schedule."""

    miners: tuple[str, ...]
    launch_order: tuple[int, ...]
    launch_delays: tuple[float, ...]


def plan_trial(config: TrialConfig) -> LaunchPlan:
    """Derive miner identities, launch order and delays deterministically from the seed.

    neural-v3 miners are valid TEST reward addresses derived from a hash. No private
    key exists for them, so their rewards can never be spent.

    Args:
        config: Trial inputs; validated by the caller.

    Returns:
        A plan that is identical for identical configurations.
    """
    rng = random.Random(f"verunai-p0|{config.seed}")
    miners = []
    for index in range(config.nodes):
        material = hashlib.sha256(f"verunai-p0-miner|{config.seed}|{index}".encode()).hexdigest()
        if config.protocol == "neural-v3":
            miners.append(address_from_public_hex(material))
        else:
            miners.append(f"p0n{index}-{material[:8]}")
    order = list(range(config.nodes))
    rng.shuffle(order)
    delays = tuple(round(rng.uniform(0.0, 0.25), 3) for _ in range(config.nodes))
    return LaunchPlan(tuple(miners), tuple(order), delays)


def converged(statuses: list[dict], target_height: int) -> bool:
    """Return whether every node reports the same head at or above the target height."""
    if not statuses:
        return False
    heads = {status.get("head") for status in statuses}
    return len(heads) == 1 and all(int(status.get("height", -1)) >= target_height
                                   for status in statuses)


def ledger_fingerprint(protocol: str, exported: dict) -> dict:
    """Re-verify an exported chain from genesis and summarise its ledger state.

    Args:
        protocol: Protocol that produced the export.
        exported: Chain export as saved by a node.

    Returns:
        Height, head, balances, v3 sequences and transfer count, a model digest and
        a SHA-256 of the canonical export.

    Raises:
        ValueError: If the protocol's own validator rejects the chain.
    """
    chain = PROTOCOLS[protocol].import_and_verify(exported)
    if protocol == "bigram-v1":
        model_digest = hashlib.sha256(canonical_bytes(chain.counts)).hexdigest()
    else:
        model_digest = weights_digest(chain.weights)
    return {
        "height": len(chain.blocks),
        "head": chain.head,
        "balances": dict(sorted(chain.balances.items())),
        "sequences": dict(sorted(getattr(chain, "sequences", {}).items())),
        "confirmed_transfers": len(getattr(chain, "included_txids", ())),
        "model_digest": model_digest,
        "export_sha256": hashlib.sha256(canonical_bytes(chain.export())).hexdigest(),
    }


def compare_fingerprints(fingerprints: list[dict]) -> list[str]:
    """Return the ledger fields on which any node disagrees (empty when all agree)."""
    if not fingerprints:
        return ["no ledgers"]
    return sorted(key for key in fingerprints[0]
                  if any(item.get(key) != fingerprints[0][key] for item in fingerprints[1:]))


def run_trial(config: TrialConfig) -> dict:
    """Run one complete trial and return a JSON-serialisable record.

    Failures are recorded in the result rather than raised, so a campaign keeps
    every failed trial as evidence. Invalid controls still raise ``ValueError``.
    """
    config.validate()
    plan = plan_trial(config)
    record: dict = {"seed": config.seed, "config": asdict(config), "plan": asdict(plan),
                    "result": "FAIL", "failure_kind": None, "failure_detail": None,
                    "port_retries": 0, "pids": []}
    for attempt in range(3):
        try:
            with tempfile.TemporaryDirectory(prefix="verunai-p0-",
                                             ignore_cleanup_errors=True) as directory:
                record.update(_run_trial_once(config, plan, Path(directory), record["pids"]))
            record["result"] = "PASS"
            record["failure_kind"] = record["failure_detail"] = None
            return record
        except TrialFailure as failure:
            record["failure_kind"], record["failure_detail"] = failure.kind, str(failure)[:2000]
            details = getattr(failure, "partial", None)
            if details:
                record.update(details)
            if failure.kind != "port_in_use":
                return record
            record["port_retries"] = attempt + 1
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            # Unexpected harness faults are evidence too; nodes were already stopped.
            record["failure_kind"] = "harness_error"
            record["failure_detail"] = f"{type(error).__name__}: {error}"[:2000]
            return record
    return record


def _run_trial_once(config: TrialConfig, plan: LaunchPlan, directory: Path,
                    pids: list[int]) -> dict:
    node_ports = _free_ports(config.nodes)
    relays = [CountingRelay(port) for port in node_ports] if config.use_relays else []
    peer_ports = [relay.start() for relay in relays] if relays else list(node_ports)
    processes: list[subprocess.Popen | None] = [None] * config.nodes
    logs: list = []
    timings: dict = {}
    statuses: list[dict] = []
    resources: list[dict] = []
    partial: dict = {}
    try:
        start = time.monotonic()
        for index in plan.launch_order:
            time.sleep(plan.launch_delays[index])
            processes[index], log = _launch_node(config, plan, index, node_ports, peer_ports,
                                                 directory)
            logs.append(log)
            pids.append(processes[index].pid)
        _wait_ready(processes, node_ports, directory, start + config.timeout)
        timings["all_ready_s"] = round(time.monotonic() - start, 3)
        statuses = _wait_converged(config, processes, node_ports, directory, start, timings)
        timings["converged_s"] = round(time.monotonic() - start, 3)
        resources = [sample_process(process.pid) for process in processes]
        partial = {"timings": timings, "nodes": _summarise_nodes(plan, statuses, resources,
                                                                 relays)}
    except TrialFailure as failure:
        failure.partial = {"timings": timings,
                           "stderr_tails": _stderr_tails(directory, config.nodes)}
        raise
    finally:
        orphans = _stop_all([p for p in processes if p is not None])
        for relay in relays:
            relay.stop()
        for handle in logs:
            handle.close()
    if orphans:
        raise TrialFailure("orphan_process", f"Processes survived shutdown: {orphans}")
    audits = [_audit_node(config.protocol, directory / f"node{index}.json")
              for index in range(config.nodes)]
    mismatches = compare_fingerprints([audit["fingerprint"] for audit in audits])
    for index, audit in enumerate(audits):
        if audit["fingerprint"]["head"] != statuses[index]["head"]:
            mismatches.append(f"node{index}: saved head differs from reported head")
    if mismatches:
        failure = TrialFailure("ledger_mismatch", "Ledgers disagree on: " + ", ".join(mismatches))
        failure.partial = {**partial, "audits": audits}
        raise failure
    return {**partial, "audits": audits, "ledger": audits[0]["fingerprint"],
            "network_total_bytes": sum(n["network"]["bytes_to_node"] + n["network"]["bytes_from_node"]
                                       for n in partial["nodes"]) if relays else None}


def _free_ports(count: int) -> list[int]:
    ports: set[int] = set()
    while len(ports) < count:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((LOOPBACK, 0))
            ports.add(int(sock.getsockname()[1]))
    return list(ports)


def _node_environment() -> dict:
    env = {key: value for key, value in os.environ.items() if key not in _PROXY_ENVIRONMENT}
    env["NO_PROXY"] = env["no_proxy"] = "127.0.0.1,localhost"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(REPOSITORY_ROOT), env.get("PYTHONPATH")]))
    return env


def _launch_node(config: TrialConfig, plan: LaunchPlan, index: int, node_ports: list[int],
                 peer_ports: list[int], directory: Path):
    difficulty = int(config.node_difficulty_overrides.get(index, config.difficulty))
    command = [sys.executable, "-m", "verunai", "node", "--protocol", config.protocol,
               "--miner", plan.miners[index], "--host", LOOPBACK,
               "--port", str(node_ports[index]), "--difficulty", str(difficulty),
               "--mine", "--max-blocks", str(config.target_height),
               "--storage", str(directory / f"node{index}.json"),
               "--sync-interval", str(config.sync_interval)]
    for other, port in enumerate(peer_ports):
        if other != index:
            command += ["--peer", f"http://{LOOPBACK}:{port}"]
    log = open(directory / f"node{index}.log", "w", encoding="utf-8")
    process = subprocess.Popen(command, cwd=REPOSITORY_ROOT, env=_node_environment(),
                               stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    return process, log


def _fetch_status(port: int) -> dict:
    with _DIRECT.open(f"http://{LOOPBACK}:{port}/status", timeout=1.0) as response:
        raw = response.read(STATUS_LIMIT_BYTES + 1)
    if len(raw) > STATUS_LIMIT_BYTES:
        raise ValueError("Status response too large")
    status = json.loads(raw)
    if not isinstance(status, dict):
        raise ValueError("Status must be a JSON object")
    return status


def _check_alive(processes: list, directory: Path) -> None:
    for index, process in enumerate(processes):
        if process.poll() is not None:
            tail = _read_tail(directory / f"node{index}.log")
            kind = "port_in_use" if ("address already in use" in tail.lower()
                                     or "10048" in tail or "10013" in tail) else "node_exited"
            raise TrialFailure(kind, f"node{index} exited with code {process.returncode}: {tail}")


def _wait_ready(processes: list, ports: list[int], directory: Path, deadline: float) -> None:
    pending = set(range(len(ports)))
    while pending:
        _check_alive(processes, directory)
        if time.monotonic() > deadline:
            raise TrialFailure("startup_timeout", f"Nodes never answered /status: {sorted(pending)}")
        for index in list(pending):
            try:
                _fetch_status(ports[index])
                pending.discard(index)
            except (OSError, ValueError):
                pass
        time.sleep(POLL_INTERVAL)


def _wait_converged(config: TrialConfig, processes: list, ports: list[int], directory: Path,
                    start: float, timings: dict) -> list[dict]:
    deadline = start + config.timeout
    stable_since = None
    last: list[dict] = []
    while time.monotonic() < deadline:
        _check_alive(processes, directory)
        try:
            last = [_fetch_status(port) for port in ports]
        except (OSError, ValueError):
            time.sleep(POLL_INTERVAL)
            continue
        if "first_block_s" not in timings and any(int(s.get("height", 0)) >= 1 for s in last):
            timings["first_block_s"] = round(time.monotonic() - start, 3)
        if converged(last, config.target_height):
            stable_since = stable_since or time.monotonic()
            if time.monotonic() - stable_since >= STABLE_WINDOW:
                return last
        else:
            stable_since = None
        time.sleep(POLL_INTERVAL)
    observed = [(s.get("height"), str(s.get("head", ""))[:12]) for s in last]
    raise TrialFailure("not_converged", f"No common head at height {config.target_height} "
                                        f"within {config.timeout}s; observed {observed}")


def _summarise_nodes(plan: LaunchPlan, statuses: list[dict], resources: list[dict],
                     relays: list[CountingRelay]) -> list[dict]:
    nodes = []
    for index, status in enumerate(statuses):
        nodes.append({"index": index, "miner": plan.miners[index],
                      "reported_height": status.get("height"), "reported_head": status.get("head"),
                      "stats": status.get("stats", {}), "resources": resources[index],
                      "network": relays[index].counts() if relays else None})
    return nodes


def _stop_all(processes: list) -> list[int]:
    """Stop nodes (SIGINT then kill on POSIX; TerminateProcess on Windows) and list survivors."""
    for process in processes:
        if process.poll() is None:
            if os.name == "nt":
                process.terminate()
            else:
                process.send_signal(signal.SIGINT)
    deadline = time.monotonic() + 5
    for process in processes:
        try:
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
    return [process.pid for process in processes if process.poll() is None or pid_alive(process.pid)]


def _audit_node(protocol: str, storage: Path) -> dict:
    if not storage.exists():
        raise TrialFailure("missing_storage", f"{storage.name} was not written")
    try:
        exported = json.loads(storage.read_text(encoding="utf-8"))
        fingerprint = ledger_fingerprint(protocol, exported)
    except (ValueError, KeyError, TypeError) as error:
        raise TrialFailure("invalid_storage", f"{storage.name}: {error}") from error
    # Second, fully independent check: the existing CLI auditor in a fresh process.
    completed = subprocess.run([sys.executable, "-m", "verunai", "audit", str(storage)],
                               cwd=REPOSITORY_ROOT, env=_node_environment(), capture_output=True,
                               text=True, timeout=120)
    cli_valid = completed.returncode == 0 and fingerprint["head"] in completed.stdout
    if not cli_valid:
        raise TrialFailure("cli_audit_failed", f"{storage.name}: {completed.stderr[-500:]}")
    return {"storage": storage.name, "storage_bytes": storage.stat().st_size,
            "fingerprint": fingerprint, "cli_audit": "VALID"}


def _read_tail(path: Path, limit: int = 1500) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError:
        return ""


def _stderr_tails(directory: Path, count: int) -> dict:
    return {f"node{index}": _read_tail(directory / f"node{index}.log", 600) for index in range(count)}


def _nearest_rank(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * percentile // 100))
    return ordered[int(rank) - 1]


def summarise_campaign(trials: list[dict]) -> dict:
    """Aggregate pass counts, failure kinds and the distributions of measured values."""
    passed = [trial for trial in trials if trial["result"] == "PASS"]
    failures: dict[str, int] = {}
    for trial in trials:
        if trial["result"] != "PASS":
            failures[trial["failure_kind"]] = failures.get(trial["failure_kind"], 0) + 1

    def describe(values: list) -> dict | None:
        values = [v for v in values if v is not None]
        if not values:
            return None
        return {"n": len(values), "min": min(values), "median": statistics.median(values),
                "p95_nearest_rank": _nearest_rank(values, 95), "max": max(values)}

    nodes = [node for trial in passed for node in trial["nodes"]]
    return {
        "trials": len(trials), "passed": len(passed), "failed": len(trials) - len(passed),
        "failures_by_kind": failures,
        "converged_s": describe([t["timings"]["converged_s"] for t in passed]),
        "first_block_s": describe([t["timings"].get("first_block_s") for t in passed]),
        "trials_with_reorganization": sum(
            any(n["stats"].get("chain_reorganizations", 0) for n in t["nodes"]) for t in passed),
        "reorganizations_total": sum(n["stats"].get("chain_reorganizations", 0) for n in nodes),
        "rejected_blocks_total": sum(n["stats"].get("rejected_blocks", 0) for n in nodes),
        "node_cpu_seconds": describe([n["resources"]["cpu_seconds"] for n in nodes]),
        "node_peak_rss_bytes": describe([n["resources"]["peak_rss_bytes"] for n in nodes]),
        "network_bytes_per_trial": describe([t.get("network_total_bytes") for t in passed]),
    }


def run_campaign(base_config: TrialConfig, trials: int, base_seed: int) -> dict:
    """Run sequential trials with seeds ``base_seed .. base_seed + trials - 1``."""
    if not 1 <= trials <= 100:
        raise ValueError("trials must be 1..100")
    records = []
    for offset in range(trials):
        config = TrialConfig(**{**asdict(base_config), "seed": base_seed + offset})
        record = run_trial(config)
        records.append(record)
        print(f"trial seed={config.seed}: {record['result']}"
              + (f" ({record['failure_kind']})" if record["failure_kind"] else ""),
              file=sys.stderr, flush=True)
    return {
        "experiment": "verunai-v0.8-P0-three-node-harness",
        "scope": "Unmodified v0.6 nodes, separate OS processes, 127.0.0.1 only, TEST units only",
        "environment": _environment(),
        "base_config": {k: v for k, v in asdict(base_config).items() if k != "seed"},
        "base_seed": base_seed,
        "summary": summarise_campaign(records),
        "trials": records,
    }


def _environment() -> dict:
    import platform
    return {"platform": platform.platform(), "python": platform.python_version(),
            "processor": platform.processor(), "logical_cpus": os.cpu_count(),
            "metrics_warning": launcher_warning()}


def main() -> int:
    """Command-line entry point; prints the campaign JSON and exits 1 if any trial failed."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--protocol", choices=sorted(PROTOCOLS), default="neural-v3")
    parser.add_argument("--nodes", type=int, default=3)
    parser.add_argument("--difficulty", type=int, default=2)
    parser.add_argument("--height", type=int, default=10)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--base-seed", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--sync-interval", type=float, default=0.2)
    parser.add_argument("--no-relays", action="store_true",
                        help="Connect nodes directly (disables traffic counting)")
    parser.add_argument("--output", type=Path, help="Also write the JSON report to this new file")
    args = parser.parse_args()
    config = TrialConfig(seed=args.base_seed, protocol=args.protocol, nodes=args.nodes,
                         difficulty=args.difficulty, target_height=args.height,
                         timeout=args.timeout, sync_interval=args.sync_interval,
                         use_relays=not args.no_relays)
    try:
        config.validate()
        if args.output and args.output.exists():
            raise ValueError(f"Refusing to overwrite {args.output}")
        report = run_campaign(config, args.trials, args.base_seed)
    except ValueError as error:
        parser.error(str(error))
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
