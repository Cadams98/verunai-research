"""Local/private-network experimental Verunai nodes (v1, v2 and v3).

A real multi-process HTTP testnet, NOT secure p2p consensus. Peer URLs are
explicit, transport is unauthenticated, and this module must not be exposed to
the public Internet. Only fictional test units exist.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from typing import Any

from .core import Block, Chain, make_candidate
from .neural_consensus import (NeuralBlock, NeuralChain, neural_candidate,
                                NETWORK_ID as NEURAL_NETWORK_ID, weights_digest)
from .neural_v3 import (LedgerBlock, LedgerChain, ledger_candidate,
                        NETWORK_ID as LEDGER_NETWORK_ID, MAX_TXS)
from .wallet import Transfer, ADDRESS_RE

NETWORK_ID = "verunai-research-private-v1"
MAX_REQUEST_BYTES = 512_000
MAX_CHAIN_BYTES = 5_000_000
MAX_SYNC_BLOCKS = 3_000
HTTP_TIMEOUT = 2.0
MINER_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,40}\Z")


def validate_peer_url(peer: str) -> str:
    url = urlsplit(peer)
    if (url.scheme != "http" or not url.hostname or url.username is not None
            or url.password is not None or url.path not in ("", "/")
            or url.query or url.fragment or not url.port
            or not 1 <= url.port <= 65535):
        raise ValueError("Peer must be http://HOST:PORT (no path, credentials, or query)")
    return f"http://{url.hostname}:{url.port}"


def request_json(url: str, payload: dict | None = None, limit: int = MAX_CHAIN_BYTES) -> dict:
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"} if data else {},
                  method="POST" if data is not None else "GET")
    with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        if int(resp.headers.get("Content-Length", "0")) > limit:
            raise ValueError("Peer response too large")
        raw = resp.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("Peer response too large")
        obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("Expected JSON object")
    return obj


class TestnetNode:
    """A fixed-difficulty chain, miner, and explicit-peer transport.

    Nodes sync by replaying peer chains and adopt the highest verified block
    count, breaking equal-height ties by lexicographically smaller tip hash.
    This is a deterministic *demo fork-choice*, not production consensus.
    """
    def __init__(self, *, miner: str, difficulty: int = 2, peers: list[str] | None = None,
                 storage: str | Path | None = None, mine: bool = False,
                 max_blocks: int = 0, sync_interval: float = 0.5,
                 attempts_per_batch: int = 32, mode: str = "bigram-v1",
                 backend: str = "python", mine_after_tx: bool = False) -> None:
        if not isinstance(miner, str) or (not ADDRESS_RE.fullmatch(miner) if mode == "neural-v3" else not MINER_ID_RE.fullmatch(miner)):
            raise ValueError("miner must be a wallet address for neural-v3, otherwise an ASCII 1-40 label")
        if max_blocks < 0 or max_blocks > MAX_SYNC_BLOCKS:
            raise ValueError("max_blocks must be 0..3000 (0 means unlimited)")
        if not 0.05 <= sync_interval <= 120:
            raise ValueError("sync_interval must be 0.05..120 seconds")
        if not 1 <= attempts_per_batch <= 512:
            raise ValueError("attempts_per_batch must be 1..512")
        if mode not in ("bigram-v1", "neural-v2", "neural-v3"):
            raise ValueError("mode must be bigram-v1, neural-v2 or neural-v3")
        if backend != "python" and (mode not in ("neural-v2", "neural-v3") or backend not in ("torch-cpu", "torch-cuda")):
            raise ValueError("torch backends supported only with neural-v2")
        if backend != "python":
            try:
                import torch
            except ImportError as exc:
                raise ValueError("PyTorch required for torch mining backend") from exc
            if backend == "torch-cuda" and not torch.cuda.is_available():
                raise ValueError("CUDA unavailable; choose --backend python or install CUDA PyTorch")
        self.mode = mode
        self.backend = backend
        self.network_id = {"bigram-v1": NETWORK_ID, "neural-v2": NEURAL_NETWORK_ID,
                           "neural-v3": LEDGER_NETWORK_ID}[mode]
        self.block_class = {"bigram-v1": Block, "neural-v2": NeuralBlock,
                            "neural-v3": LedgerBlock}[mode]
        self.chain_class = {"bigram-v1": Chain, "neural-v2": NeuralChain,
                            "neural-v3": LedgerChain}[mode]
        self.miner = miner
        self.peers = list(dict.fromkeys(validate_peer_url(p) for p in (peers or [])))
        self.storage = Path(storage) if storage is not None else None
        self.chain = self.chain_class(difficulty)
        if self.storage and self.storage.exists():
            saved = json.loads(self.storage.read_text(encoding="utf-8"))
            restored = self.chain_class.import_and_verify(saved)
            if restored.difficulty != difficulty:
                raise ValueError("Stored chain difficulty differs from configured difficulty")
            if len(restored.blocks) > MAX_SYNC_BLOCKS:
                raise ValueError("Stored chain exceeds research safety limit")
            self.chain = restored
        self.mine_enabled = mine
        self.mine_after_tx = mine_after_tx
        self.max_blocks = max_blocks
        self.sync_interval = sync_interval
        self.attempts_per_batch = attempts_per_batch
        self.lock = threading.RLock()
        self.pending: dict[str, Transfer] = {}
        self.stop_event = threading.Event()
        self.server: ThreadingHTTPServer | None = None
        self.threads: list[threading.Thread] = []
        self.stats = {"local_blocks_mined": 0, "peer_blocks_received": 0,
                      "chain_reorganizations": 0, "peer_syncs": 0,
                      "rejected_blocks": 0, "candidate_attempts": 0}

    def _persist(self) -> None:
        """Must be called with self.lock held."""
        if not self.storage:
            return
        self.storage.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(self.chain.export(), indent=2)
        tmp = self.storage.with_name(self.storage.name + ".tmp")
        tmp.write_text(serialized, encoding="utf-8")
        os.replace(tmp, self.storage)

    def status(self) -> dict:
        with self.lock:
            return {"network_id": self.network_id, "protocol_mode": self.mode,
                    "compute_backend": self.backend, "miner": self.miner,
                    "height": len(self.chain.blocks), "head": self.chain.head,
                    "difficulty": self.chain.difficulty,
                    "balances": dict(self.chain.balances),
                    "training_loss": round(self.chain.training_loss() if self.mode in ("neural-v2", "neural-v3") else self.chain.cross_entropy(), 6),
                    "pending_transfers": len(self.pending),
                    "sequences": dict(self.chain.sequences) if self.mode == "neural-v3" else {},
                    "peers": list(self.peers), "mining": self.mine_enabled,
                    "stats": dict(self.stats),
                    "warning": "No real coins; no secure consensus, production wallets, or public-network security"}

    def export(self) -> dict:
        with self.lock:
            return self.chain.export()

    def pending_transfers(self) -> list[Transfer]:
        with self.lock:
            return sorted(self.pending.values(), key=lambda t: (t.sender, t.sequence, t.txid))

    def _prune_mempool(self) -> None:
        """Keep only transfers that form a valid sequence from current state."""
        if self.mode != "neural-v3":
            return
        retained = {}
        for tx in self.pending_transfers():
            try:
                self.chain.check_transfers(list(retained.values()) + [tx])
            except ValueError:
                continue
            retained[tx.txid] = tx
        self.pending = retained

    def submit_transfer(self, payload: dict) -> tuple[bool, str]:
        if self.mode != "neural-v3":
            return False, "Transfers require neural-v3 protocol"
        try:
            tx = Transfer.from_dict(payload)
            with self.lock:
                if tx.txid in self.pending or tx.txid in self.chain.included_txids:
                    return False, "Transfer already known"
                if len(self.pending) >= 256:
                    return False, "Research mempool capacity reached"
                selected = self.pending_transfers()
                # Reject conflicting, unaffordable or out-of-sequence transfers.
                self.chain.check_transfers(selected + [tx])
                self.pending[tx.txid] = tx
            return True, tx.txid
        except (TypeError, ValueError, KeyError, OverflowError) as exc:
            return False, f"Invalid transfer: {str(exc)[:150]}"

    def broadcast_transfer(self, tx: Transfer) -> None:
        for peer in self.peers:
            if self.stop_event.is_set():
                return
            try:
                request_json(peer + "/tx", {"transfer": tx.to_dict()}, limit=4096)
            except (OSError, URLError, HTTPError, ValueError, TypeError):
                continue

    def accept_block(self, payload: dict, source: str = "peer") -> tuple[bool, str]:
        """Accept only direct-tip blocks; full fork resolution occurs in sync_once."""
        try:
            block = self.block_class.from_dict(payload)
            with self.lock:
                if block.height != len(self.chain.blocks) + 1 or block.prev_hash != self.chain.head:
                    return False, "Block is stale or belongs to a competing fork; sync required"
                self.chain.accept(block)
                if self.mode == "neural-v3":
                    self._prune_mempool()
                self._persist()
                if source == "peer":
                    self.stats["peer_blocks_received"] += 1
                return True, "accepted"
        except (TypeError, KeyError, IndexError, ValueError, OverflowError) as exc:
            with self.lock:
                self.stats["rejected_blocks"] += 1
            return False, f"Invalid block: {str(exc)[:180]}"

    def adopt_peer_chain(self, exported: dict) -> bool:
        """Fully replay and check a remote chain before any state replacement."""
        if not isinstance(exported, dict) or not isinstance(exported.get("blocks"), list):
            raise ValueError("Malformed chain export")
        if len(exported["blocks"]) > MAX_SYNC_BLOCKS:
            raise ValueError("Peer chain exceeds maximum test length")
        if exported.get("difficulty") != self.chain.difficulty:
            raise ValueError("Peer difficulty does not match local network")
        candidate = self.chain_class.import_and_verify(exported)
        with self.lock:
            current_key = (len(self.chain.blocks), -int(self.chain.head, 16))
            candidate_key = (len(candidate.blocks), -int(candidate.head, 16))
            if candidate_key <= current_key:
                return False
            if self.chain.blocks and candidate.blocks[:len(self.chain.blocks)] != self.chain.blocks:
                self.stats["chain_reorganizations"] += 1
            self.chain = candidate
            if self.mode == "neural-v3":
                self._prune_mempool()
            self._persist()
            self.stats["peer_syncs"] += 1
        return True

    def sync_once(self) -> bool:
        adopted = False
        for peer in self.peers:
            if self.stop_event.is_set():
                break
            try:
                remote_status = request_json(peer + "/status", limit=16_000)
                if (remote_status.get("network_id") != self.network_id or
                        remote_status.get("difficulty") != self.chain.difficulty):
                    continue
                with self.lock:
                    current_key = (len(self.chain.blocks), -int(self.chain.head, 16))
                try:
                    remote_key = (int(remote_status["height"]), -int(remote_status["head"], 16))
                except (KeyError, TypeError, ValueError):
                    continue
                if remote_key <= current_key or remote_key[0] > MAX_SYNC_BLOCKS:
                    continue
                fetched = request_json(peer + "/chain")
                adopted = self.adopt_peer_chain(fetched) or adopted
                if self.mode == "neural-v3":
                    try:
                        remote_pending = request_json(peer + "/mempool", limit=64_000)
                        for item in remote_pending.get("transfers", [])[:256]:
                            if isinstance(item, dict):
                                self.submit_transfer(item)
                    except (OSError, URLError, HTTPError, ValueError, TypeError):
                        pass
            except (OSError, URLError, HTTPError, ValueError, TypeError, KeyError, OverflowError):
                # A peer may be offline, malformed, or intentionally unhelpful.
                continue
        return adopted

    def broadcast(self, block: Block | NeuralBlock | LedgerBlock) -> None:
        for peer in self.peers:
            if self.stop_event.is_set():
                return
            try:
                request_json(peer + "/block", {"block": block.to_dict()}, limit=4_096)
            except (OSError, URLError, HTTPError, ValueError, TypeError):
                continue

    def mine_batch(self) -> bool:
        """Try candidates from a snapshot; abandon stale work when a peer wins."""
        with self.lock:
            if self.max_blocks and len(self.chain.blocks) >= self.max_blocks:
                return False
            parent, height, difficulty = self.chain.head, len(self.chain.blocks) + 1, self.chain.difficulty
            snapshot_weights = [row[:] for row in self.chain.weights] if self.mode in ("neural-v2", "neural-v3") else None
            txs = tuple(self.pending_transfers()[:MAX_TXS]) if self.mode == "neural-v3" else ()
        # Distinct workers start different nonce ranges to avoid redundant mining.
        # Random starting positions are non-consensus metadata, not randomness of work.
        seed = int.from_bytes(os.urandom(8), "big")
        for offset in range(self.attempts_per_batch):
            if self.stop_event.is_set():
                return False
            nonce = (seed + offset) % (1 << 64)
            if self.mode == "neural-v2":
                candidate = neural_candidate(height, parent, self.miner, nonce,
                                             difficulty, snapshot_weights, self.backend)
            elif self.mode == "neural-v3":
                candidate = ledger_candidate(height, parent, self.miner, nonce,
                                             difficulty, snapshot_weights, txs, self.backend)
            else:
                candidate = make_candidate(height, parent, self.miner, nonce, difficulty)
            with self.lock:
                self.stats["candidate_attempts"] += 1
                if self.chain.head != parent or (self.max_blocks and len(self.chain.blocks) >= self.max_blocks):
                    return False
            if candidate.hash.startswith("0" * difficulty):
                accepted, _ = self.accept_block(candidate.to_dict(), source="local")
                if accepted:
                    with self.lock:
                        self.stats["local_blocks_mined"] += 1
                    self.broadcast(candidate)
                    return True
        return False

    def _mine_loop(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                limit_reached = bool(self.max_blocks and len(self.chain.blocks) >= self.max_blocks)
            if limit_reached:
                self.stop_event.wait(0.1)
                continue
            if self.mine_after_tx and self.mode == "neural-v3":
                with self.lock:
                    has_tx = bool(self.pending)
                if not has_tx:
                    self.stop_event.wait(0.05)
                    continue
            self.mine_batch()

    def _sync_loop(self) -> None:
        while not self.stop_event.is_set():
            self.sync_once()
            self.stop_event.wait(self.sync_interval)

    def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        if self.server is not None:
            raise RuntimeError("Node already running")
        node = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_: Any) -> None:
                return

            def send_json(self, status_code: int, obj: dict) -> None:
                encoded = json.dumps(obj, separators=(",", ":")).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    self.wfile.write(encoded)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self) -> None:
                if self.path == "/health":
                    self.send_json(200, {"ok": True, "network_id": node.network_id})
                elif self.path == "/status":
                    self.send_json(200, node.status())
                elif self.path == "/chain":
                    self.send_json(200, node.export())
                elif self.path == "/mempool" and node.mode == "neural-v3":
                    self.send_json(200, {"transfers": [t.to_dict() for t in node.pending_transfers()]})
                elif self.path == "/model":
                    with node.lock:
                        if node.mode in ("neural-v2", "neural-v3"):
                            self.send_json(200, {"type": "integer-linear-neural-model-" + node.mode,
                                                 "blocks_trained": len(node.chain.blocks),
                                                 "training_mse": node.chain.training_loss(),
                                                 "model_digest": weights_digest(node.chain.weights),
                                                 "dimension": len(node.chain.weights)})
                        else:
                            self.send_json(200, {"type": "toy-character-transition-model",
                                                 "blocks_trained": len(node.chain.blocks),
                                                 "training_loss": node.chain.cross_entropy(),
                                                 "vocab_size": len(node.chain.counts),
                                                 "update_count": sum(sum(row) for row in node.chain.counts)})
                else:
                    self.send_json(404, {"error": "Unknown path"})

            def do_POST(self) -> None:
                if self.path not in ("/block", "/tx"):
                    self.send_json(404, {"error": "Unknown path"})
                    return
                try:
                    size = int(self.headers.get("Content-Length", "-1"))
                    if not 1 <= size <= MAX_REQUEST_BYTES:
                        self.send_json(413, {"error": "Invalid or oversized payload"})
                        return
                    incoming = json.loads(self.rfile.read(size))
                    if not isinstance(incoming, dict):
                        raise ValueError("Expected object")
                    if self.path == "/tx":
                        if not isinstance(incoming.get("transfer"), dict):
                            raise ValueError("Expected transfer")
                        accepted, detail = node.submit_transfer(incoming["transfer"])
                        if accepted:
                            self.send_json(200, {"accepted": True, "txid": detail})
                            threading.Thread(target=node.broadcast_transfer, args=(Transfer.from_dict(incoming["transfer"]),), daemon=True).start()
                        else:
                            self.send_json(422, {"accepted": False, "reason": detail})
                        return
                    if not isinstance(incoming.get("block"), dict):
                        raise ValueError("Expected block JSON object")
                    accepted, detail = node.accept_block(incoming["block"])
                    if accepted:
                        self.send_json(200, {"accepted": True, "height": node.status()["height"]})
                        threading.Thread(target=node.broadcast, args=(node.block_class.from_dict(incoming["block"]),), daemon=True).start()
                    else:
                        self.send_json(409 if "stale" in detail else 422,
                                       {"accepted": False, "reason": detail})
                        if "stale" in detail:
                            threading.Thread(target=node.sync_once, daemon=True).start()
                except (ValueError, TypeError, UnicodeDecodeError, KeyError, IndexError) as exc:
                    self.send_json(400, {"error": str(exc)[:150]})

        self.server = ThreadingHTTPServer((host, port), Handler)
        self.server.daemon_threads = True
        assigned_port = int(self.server.server_address[1])
        self.threads.append(threading.Thread(target=self.server.serve_forever, name="http", daemon=True))
        self.threads.append(threading.Thread(target=self._sync_loop, name="sync", daemon=True))
        if self.mine_enabled:
            self.threads.append(threading.Thread(target=self._mine_loop, name="mine", daemon=True))
        for thread in self.threads:
            thread.start()
        return assigned_port

    def stop(self) -> None:
        self.stop_event.set()
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=3.0)
