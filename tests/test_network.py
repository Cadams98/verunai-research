import copy
import http.client
import json
import tempfile
import time
import unittest
from pathlib import Path

from verunai.core import Chain, mine_round_robin
from verunai.demo import demo_testnet
from verunai.network import TestnetNode, request_json, validate_peer_url


class TestPrivateTestnet(unittest.TestCase):
    def test_invalid_peer_urls_rejected(self):
        for url in ("https://example.org:1234", "http://host", "http://alice:secret@host:20",
                    "http://host:99/path", "file:///tmp/a", "http://host:70000"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_peer_url(url)

    def test_http_block_propagation_and_independent_validation(self):
        a = TestnetNode(miner="alice", difficulty=1)
        b = TestnetNode(miner="bob", difficulty=1)
        pa, pb = a.start(port=0), b.start(port=0)
        try:
            a.peers = [f"http://127.0.0.1:{pb}"]
            b.peers = [f"http://127.0.0.1:{pa}"]
            for _ in range(200):
                if a.mine_batch():
                    break
            else:
                self.fail("Miner did not find a difficulty-1 block")
            deadline = time.monotonic() + 5
            while b.chain.head != a.chain.head and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertEqual(a.chain.head, b.chain.head)
            remote = request_json(f"http://127.0.0.1:{pb}/chain")
            self.assertEqual(Chain.import_and_verify(remote).head, a.chain.head)
            self.assertEqual(request_json(f"http://127.0.0.1:{pb}/model")["blocks_trained"], 1)
            self.assertEqual(sum(b.chain.balances.values()), 50)
        finally:
            a.stop()
            b.stop()

    def test_late_joiner_synchronizes_complete_verified_history(self):
        a = TestnetNode(miner="alice", difficulty=1)
        for _ in range(3):
            mine_round_robin(a.chain, {"alice": 1})
        pa = a.start(port=0)
        b = TestnetNode(miner="bob", difficulty=1, peers=[f"http://127.0.0.1:{pa}"])
        try:
            b.sync_once()
            self.assertEqual(b.chain.head, a.chain.head)
            self.assertEqual(b.chain.counts, a.chain.counts)
            self.assertEqual(b.chain.balances, a.chain.balances)
            self.assertEqual(b.stats["peer_syncs"], 1)
        finally:
            a.stop()

    def test_fork_choice_uses_fully_verified_chains(self):
        a = TestnetNode(miner="alice", difficulty=1)
        b = TestnetNode(miner="bob", difficulty=1)
        mine_round_robin(a.chain, {"alice": 1})
        mine_round_robin(b.chain, {"bob": 1})
        expected = min(a.chain.head, b.chain.head)
        a.adopt_peer_chain(b.chain.export())
        b.adopt_peer_chain(a.chain.export())
        self.assertEqual(a.chain.head, expected)
        self.assertEqual(b.chain.head, expected)

    def test_reject_tampered_longer_peer_chain_without_mutating_state(self):
        a = TestnetNode(miner="alice", difficulty=1)
        b = TestnetNode(miner="bob", difficulty=1)
        mine_round_robin(b.chain, {"bob": 1})
        mine_round_robin(b.chain, {"bob": 1})
        forged = copy.deepcopy(b.chain.export())
        forged["blocks"][1]["reward"] = 999999
        old_head = a.chain.head
        with self.assertRaises(ValueError):
            a.adopt_peer_chain(forged)
        self.assertEqual(a.chain.head, old_head)

    def test_chain_persistence_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            filename = Path(tmp) / "chain.json"
            a = TestnetNode(miner="alice", difficulty=1, storage=filename)
            for _ in range(200):
                if a.mine_batch():
                    break
            self.assertTrue(filename.exists())
            loaded = TestnetNode(miner="alice", difficulty=1, storage=filename)
            self.assertEqual(loaded.chain.head, a.chain.head)
            with self.assertRaises(ValueError):
                TestnetNode(miner="alice", difficulty=2, storage=filename)

    def test_reject_large_or_malformed_http_requests(self):
        n = TestnetNode(miner="alice", difficulty=1)
        port = n.start(port=0)
        try:
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            c.request("POST", "/block", body=b"{}", headers={"Content-Length": "999999999"})
            resp = c.getresponse()
            self.assertEqual(resp.status, 413)
            resp.read()
            c.close()
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            c.request("POST", "/block", body=b'{"block": []}',
                      headers={"Content-Type": "application/json"})
            resp = c.getresponse()
            self.assertEqual(resp.status, 400)
            resp.read()
            c.close()
            self.assertEqual(n.chain.head, "0" * 64)
        finally:
            n.stop()

    def test_two_real_processes_mine_and_converge(self):
        result = demo_testnet(blocks=5, difficulty=1, timeout=20)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["independent_processes"], 2)
        self.assertEqual(result["chain_height"], 5)
        self.assertEqual(sum(result["balances"].values()), 5 * 50)


if __name__ == "__main__":
    unittest.main()
