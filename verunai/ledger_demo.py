"""Two independent HTTP nodes: mine test units, signed transfer, mine confirmation."""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from .network import TestnetNode, request_json
from .neural_v3 import LedgerChain
from .wallet import Wallet, sign_transfer


def demo_ledger() -> dict:
    alice = Wallet.generate()
    bob = Wallet.generate()
    a = TestnetNode(miner=alice.address, mode="neural-v3", difficulty=1, attempts_per_batch=64)
    b = TestnetNode(miner=bob.address, mode="neural-v3", difficulty=1, attempts_per_batch=64)
    pa = a.start(port=0)
    pb = b.start(port=0)
    try:
        a.peers = [f"http://127.0.0.1:{pb}"]
        b.peers = [f"http://127.0.0.1:{pa}"]
        for _ in range(100):
            if a.mine_batch():
                break
        else:
            raise RuntimeError("Alice did not mine test reward")
        b.sync_once()
        if b.chain.head != a.chain.head:
            raise RuntimeError("Nodes diverged before payment")
        tx = sign_transfer(alice, bob.address, amount=12, fee=1, sequence=0)
        receipt = request_json(f"http://127.0.0.1:{pa}/tx", {"transfer": tx.to_dict()})
        if not receipt.get("accepted"):
            raise RuntimeError("Payment was rejected by Alice's node")
        # The signed transfer is gossiped; also submit directly to B for a
        # deterministic demo if the optional broadcast has not finished yet.
        if tx.txid not in b.pending:
            b.submit_transfer(tx.to_dict())
        for _ in range(100):
            if b.mine_batch():
                break
        else:
            raise RuntimeError("Bob did not mine confirmation")
        a.sync_once()
        if a.chain.head != b.chain.head:
            raise RuntimeError("Nodes diverged after payment")
        replay = LedgerChain.import_and_verify(a.export())
        if (replay.balances != a.chain.balances or replay.weights != b.chain.weights
            or replay.balances.get(alice.address) != 37
            or replay.balances.get(bob.address) != 63):
            raise RuntimeError("Balance, signature or model replay failed")
        return {"result": "PASS", "protocol": "neural-v3", "nodes": 2,
                "confirmed_height": len(replay.blocks), "transaction_id": tx.txid,
                "sender": alice.address, "recipient": bob.address,
                "sent_TEST": 12, "miner_fee_TEST": 1,
                "alice_balance_TEST": replay.balances[alice.address],
                "bob_balance_TEST": replay.balances[bob.address],
                "total_TEST_issued": sum(replay.balances.values()),
                "chains_match": a.chain.head == b.chain.head,
                "models_match": a.chain.weights == b.chain.weights,
                "independent_replay": True,
                "real_money": False,
                "security_warning": "Local educational blockchain. Not a production wallet, safe public network, or proof of useful AI work."}
    finally:
        a.stop()
        b.stop()
