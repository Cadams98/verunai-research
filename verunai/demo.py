"""Reproducible two-OS-process, local-only testnet demonstration."""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .network import request_json


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def demo_testnet(blocks: int = 8, difficulty: int = 2, timeout: float = 30.0,
                 mode: str = "bigram-v1", backend: str = "python") -> dict:
    """Spawn and exercise two independent Python miner processes, then audit disks."""
    if not 2 <= blocks <= 100:
        raise ValueError("demo blocks must be 2..100")
    if not 1 <= difficulty <= 3:
        raise ValueError("demo difficulty must be 1..3")
    if not 3 <= timeout <= 120:
        raise ValueError("demo timeout must be 3..120 seconds")
    from .core import Chain
    from .neural_consensus import NeuralChain, weights_digest
    if mode not in ("bigram-v1", "neural-v2"):
        raise ValueError("Invalid protocol mode")
    if backend != "python" and (mode != "neural-v2" or backend not in ("torch-cpu", "torch-cuda")):
        raise ValueError("Invalid protocol backend")
    chain_class = NeuralChain if mode == "neural-v2" else Chain
    with tempfile.TemporaryDirectory(prefix="verunai-testnet-") as directory:
        ports = [free_port(), free_port()]
        while ports[1] == ports[0]:
            ports[1] = free_port()
        processes: list[subprocess.Popen] = []
        try:
            for i, name in enumerate(("alice", "bob")):
                other = 1 - i
                cmd = [sys.executable, "-m", "verunai", "node",
                       "--miner", name, "--port", str(ports[i]),
                       "--peer", f"http://127.0.0.1:{ports[other]}",
                       "--difficulty", str(difficulty), "--protocol", mode,
                       "--backend", backend, "--mine",
                       "--max-blocks", str(blocks),
                       "--storage", str(Path(directory) / f"{name}.json"),
                       "--sync-interval", "0.2"]
                processes.append(subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                                    stderr=subprocess.PIPE, text=True))
            deadline = time.monotonic() + timeout
            stable_since = None
            last = []
            while time.monotonic() < deadline:
                if any(p.poll() is not None for p in processes):
                    errors = [p.stderr.read()[-2000:] if p.poll() is not None else "" for p in processes]
                    raise RuntimeError("Node exited early: " + str(errors))
                try:
                    last = [request_json(f"http://127.0.0.1:{port}/status", limit=16_000)
                            for port in ports]
                except (OSError, ValueError):
                    time.sleep(0.1)
                    continue
                same = (last[0]["head"] == last[1]["head"] and
                        last[0]["height"] >= blocks)
                if same:
                    if stable_since is None:
                        stable_since = time.monotonic()
                    if time.monotonic() - stable_since >= 0.5:
                        break
                else:
                    stable_since = None
                time.sleep(0.1)
            else:
                raise TimeoutError(f"Nodes did not converge: {[(x.get('height'), x.get('head', '')[:12]) for x in last]}")
            # Read both node persistence files and independently re-verify every block.
            disk_chains = []
            for name in ("alice", "bob"):
                saved = json.loads((Path(directory) / f"{name}.json").read_text(encoding="utf-8"))
                disk_chains.append(chain_class.import_and_verify(saved))
            if disk_chains[0].head != disk_chains[1].head:
                raise AssertionError("Both disk chains must agree")
            chain = disk_chains[0]
            return {"result": "PASS", "protocol": mode, "backend": backend,
                    "independent_processes": 2,
                    "chain_height": len(chain.blocks), "same_head": True,
                    "head": chain.head, "balances": dict(chain.balances),
                    "winning_miners": [b.miner for b in chain.blocks],
                    "nodes": [{"miner": x["miner"], "height": x["height"],
                               "local_blocks_mined": x["stats"]["local_blocks_mined"],
                               "chain_reorganizations": x["stats"]["chain_reorganizations"],
                               "peer_syncs": x["stats"]["peer_syncs"]} for x in last],
                    "training_loss": chain.training_loss() if mode == "neural-v2" else round(chain.cross_entropy(), 6),
                    "model_digest": weights_digest(chain.weights) if mode == "neural-v2" else None,
                    "note": "Local test tokens only. Training-bound SHA-256 lottery; NOT secure useful-work consensus."}
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
            for process in processes:
                try:
                    process.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=3)
