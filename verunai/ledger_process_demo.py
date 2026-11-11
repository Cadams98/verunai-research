"""Full multi-process signed-transfer mining demo, loopback-only.

Launching two real Python processes is materially different from running two
node objects in one process. This is still an untrusted local TEST network.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

from .network import request_json
from .wallet import Wallet, sign_transfer
from .neural_v3 import LedgerChain


def _open_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for(url: str, pred, deadline: float, procs: list[subprocess.Popen]) -> dict:
    while time.monotonic() < deadline:
        for proc in procs:
            if proc.poll() is not None:
                raise RuntimeError(f"Node process exited unexpectedly with code {proc.returncode}")
        try:
            status = request_json(url + "/status", limit=16_000)
            if pred(status):
                return status
        except (OSError, ValueError):
            pass
        time.sleep(0.10)
    raise TimeoutError("Could not reach expected node state")


def demo_ledger_process(timeout: float = 35) -> dict:
    if not 10 <= timeout <= 300:
        raise ValueError("Timeout must be between 10 and 300 seconds")
    alice, bob = Wallet.generate(), Wallet.generate()
    a_port, b_port = _open_port(), _open_port()
    while b_port == a_port:
        b_port = _open_port()
    a_url, b_url = f"http://127.0.0.1:{a_port}", f"http://127.0.0.1:{b_port}"
    procs: list[subprocess.Popen] = []
    deadline = time.monotonic() + timeout
    with tempfile.TemporaryDirectory(prefix="verunai-v3-test-") as td:
        tmp = Path(td)
        try:
            for miner, port, peer, name, after_tx, target in [
                (alice.address, a_port, b_url, "alice", False, 1),
                (bob.address, b_port, a_url, "bob", True, 2),
            ]:
                # Keep all raw logs in this ephemeral directory; no secrets are
                # passed through environment variables or printed to users.
                log = (tmp / f"{name}.log").open("w", encoding="utf-8")
                args = [sys.executable, "-m", "verunai", "node", "--protocol", "neural-v3",
                        "--miner", miner, "--port", str(port), "--peer", peer,
                        "--difficulty", "1", "--max-blocks", str(target),
                        "--sync-interval", "0.15", "--storage", str(tmp / f"{name}.json"), "--mine"]
                if after_tx:
                    args.append("--mine-after-tx")
                proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT,
                                        stdin=subprocess.DEVNULL, cwd=str(Path(__file__).resolve().parent.parent))
                procs.append(proc)
                log.close()
                if name == "alice":
                    _wait_for(a_url, lambda st: st["height"] == 1, deadline, procs)
            _wait_for(b_url, lambda st: st["height"] == 1, deadline, procs)
            tx = sign_transfer(alice, bob.address, 12, 1, 0)
            receipt = request_json(b_url + "/tx", {"transfer": tx.to_dict()}, limit=4096)
            if not receipt.get("accepted"):
                raise RuntimeError("Signed payment not accepted")
            b_status = _wait_for(b_url, lambda st: st["height"] == 2, deadline, procs)
            a_status = _wait_for(a_url, lambda st: st["height"] == 2 and st["head"] == b_status["head"], deadline, procs)
            a_model = request_json(a_url + "/model")
            b_model = request_json(b_url + "/model")
            replayed = LedgerChain.import_and_verify(request_json(a_url + "/chain"))
            if (replayed.head != a_status["head"] or replayed.balances.get(alice.address) != 37
                or replayed.balances.get(bob.address) != 63
                or tx.txid not in replayed.included_txids):
                raise RuntimeError("Multi-process verification failed")
            return {"result": "PASS", "mode": "neural-v3", "os_processes": 2,
                    "mined_blocks": 2, "confirmed_transfers": 1, "txid": tx.txid,
                    "alice_balance_TEST": replayed.balances[alice.address],
                    "bob_balance_TEST": replayed.balances[bob.address],
                    "total_issued_TEST": sum(replayed.balances.values()),
                    "head": replayed.head, "model_digest_matches": a_model["model_digest"] == b_model["model_digest"],
                    "independent_replay": True,
                    "warning": "Only localhost TEST units; not public blockchain security or efficient useful-work proof."}
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.terminate()
            for proc in procs:
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3)
