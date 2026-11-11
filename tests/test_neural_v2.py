"""Neural-v2 correctness, fraud rejection, cross-version and networking tests."""
import copy
from dataclasses import replace
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from verunai.core import Chain, mine_round_robin
from verunai.neural_consensus import (
    NeuralChain, neural_candidate, compute_step, evaluation_mse, weights_digest,
    mine_neural, seed_batch, DIM, BATCH, REWARD, MAX_NONCE,
)
from verunai.network import TestnetNode
from verunai.demo import demo_testnet


class TestNeuralMining(unittest.TestCase):
    def test_neural_step_is_deterministic_and_updates_model(self):
        chain = NeuralChain(1)
        start_loss = chain.training_loss()
        losses = []
        for _ in range(12):
            block, _ = mine_neural(chain, {"alice": 1, "bob": 1})
            self.assertTrue(block.hash.startswith("0"))
            self.assertEqual(block.model_digest, weights_digest(chain.weights))
            losses.append(chain.training_loss())
        self.assertLess(losses[-1], start_loss)
        self.assertEqual(sum(chain.balances.values()), 12 * REWARD)
        self.assertEqual(NeuralChain.import_and_verify(chain.export()).weights, chain.weights)
        self.assertEqual(NeuralChain.import_and_verify(chain.export()).head, chain.head)

    def test_training_work_is_bound_to_parent_miner_and_nonce(self):
        chain = NeuralChain(1)
        a = compute_step(chain.weights, chain.head, "alice", 2)
        self.assertEqual(a, compute_step(chain.weights, chain.head, "alice", 2))
        self.assertNotEqual(a, compute_step(chain.weights, chain.head, "bob", 2))
        self.assertNotEqual(a, compute_step(chain.weights, chain.head, "alice", 3))
        x, y = seed_batch(chain.head, "alice", 2)
        self.assertEqual((len(x), len(x[0]), len(y), len(y[0])), (BATCH, DIM, BATCH, DIM))

    def test_forged_gradient_model_and_nonce_rejected(self):
        chain = NeuralChain(1)
        winner, _ = mine_neural(chain, {"honest": 1})
        for fake in (replace(winner, gradient_digest="0" * 64),
                     replace(winner, model_digest="0" * 64),
                     replace(winner, nonce=winner.nonce + 1),
                     replace(winner, miner="mallory")):
            with self.subTest(fake=fake), self.assertRaisesRegex(ValueError, "Neural training work invalid"):
                NeuralChain(1).accept(fake)

    def test_fake_block_reward_does_not_credit_any_balance(self):
        chain = NeuralChain(1)
        winner, _ = mine_neural(chain, {"honest": 1})
        fresh = NeuralChain(1)
        with self.assertRaisesRegex(ValueError, "Wrong neural reward"):
            fresh.accept(replace(winner, reward=5000000))
        self.assertEqual(fresh.balances, {})
        with self.assertRaisesRegex(ValueError, "Tampered neural block hash"):
            fresh.accept(replace(winner, hash="0" * 64))

    def test_v1_and_v2_cannot_replay_each_other(self):
        v1 = Chain(1)
        mine_round_robin(v1, {"alice": 1})
        v2 = NeuralChain(1)
        mine_neural(v2, {"alice": 1})
        with self.assertRaises(ValueError):
            NeuralChain.import_and_verify(v1.export())
        with self.assertRaises(ValueError):
            Chain.import_and_verify(v2.export())
        forged = copy.deepcopy(v2.export())
        forged["blocks"][0]["domain"] = "something-else"
        with self.assertRaisesRegex(ValueError, "Wrong neural protocol"):
            NeuralChain.import_and_verify(forged)

    def test_invalid_nonce_inputs_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonce"):
            seed_batch("0" * 64, "alice", -1)
        with self.assertRaisesRegex(ValueError, "nonce"):
            seed_batch("0" * 64, "alice", MAX_NONCE + 1)
        with self.assertRaisesRegex(ValueError, "nonce"):
            seed_batch("0" * 64, "alice", True)

    @unittest.skipUnless(importlib.util.find_spec("torch") is not None, "PyTorch optional")
    def test_torch_cpu_and_integer_reference_are_bit_exact(self):
        chain = NeuralChain(1)
        for nonce in (0, 1, 11, 121):
            reference = compute_step(chain.weights, chain.head, "alice", nonce, "python")
            accelerated = compute_step(chain.weights, chain.head, "alice", nonce, "torch-cpu")
            self.assertEqual(reference, accelerated)
        block = neural_candidate(1, chain.head, "alice", 0, 1, chain.weights, "torch-cpu")
        self.assertEqual(block, neural_candidate(1, chain.head, "alice", 0, 1, chain.weights))

    @unittest.skipUnless(importlib.util.find_spec("torch") is not None, "PyTorch optional")
    def test_cuda_reference_if_available(self):
        import torch
        if not torch.cuda.is_available():
            self.skipTest("CUDA GPU not present in test environment")
        chain = NeuralChain(1)
        for nonce in (0, 1, 51):
            self.assertEqual(compute_step(chain.weights, chain.head, "alice", nonce, "python"),
                             compute_step(chain.weights, chain.head, "alice", nonce, "torch-cuda"))


class TestNeuralV2Network(unittest.TestCase):
    def test_neural_nodes_gossip_and_verify(self):
        a = TestnetNode(miner="alice", difficulty=1, mode="neural-v2")
        b = TestnetNode(miner="bob", difficulty=1, mode="neural-v2")
        pa, pb = a.start(port=0), b.start(port=0)
        try:
            a.peers = [f"http://127.0.0.1:{pb}"]
            b.peers = [f"http://127.0.0.1:{pa}"]
            for _ in range(200):
                if a.mine_batch():
                    break
            else:
                self.fail("Neural miner did not find a block")
            b.sync_once()
            self.assertEqual(a.chain.head, b.chain.head)
            self.assertEqual(a.chain.weights, b.chain.weights)
            self.assertEqual(a.chain.balances, b.chain.balances)
        finally:
            a.stop()
            b.stop()

    def test_differing_protocol_peers_cannot_mix(self):
        a = TestnetNode(miner="alice", difficulty=1, mode="bigram-v1")
        b = TestnetNode(miner="bob", difficulty=1, mode="neural-v2")
        mine_neural(b.chain, {"bob": 1})
        with self.assertRaises(ValueError):
            a.adopt_peer_chain(b.chain.export())
        self.assertEqual(a.chain.head, "0" * 64)

    def test_reject_fake_neural_peer_chain_no_state_change(self):
        a = TestnetNode(miner="alice", difficulty=1, mode="neural-v2")
        b = TestnetNode(miner="bob", difficulty=1, mode="neural-v2")
        mine_neural(b.chain, {"bob": 1})
        payload = copy.deepcopy(b.chain.export())
        payload["blocks"][0]["gradient_digest"] = "0" * 64
        before = a.status()
        with self.assertRaises(ValueError):
            a.adopt_peer_chain(payload)
        self.assertEqual(a.status()["head"], before["head"])
        self.assertEqual(a.chain.weights, b.__class__(miner="genesis", difficulty=1, mode="neural-v2").chain.weights)

    def test_neural_storage_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "neural-chain.json"
            a = TestnetNode(miner="alice", difficulty=1, mode="neural-v2", storage=path)
            for _ in range(200):
                if a.mine_batch():
                    break
            self.assertTrue(path.exists())
            b = TestnetNode(miner="alice", difficulty=1, mode="neural-v2", storage=path)
            self.assertEqual(b.chain.head, a.chain.head)
            self.assertEqual(b.chain.weights, a.chain.weights)
            with self.assertRaises(ValueError):
                TestnetNode(miner="alice", difficulty=1, mode="bigram-v1", storage=path)

    def test_two_real_processes_neural_blocks_and_consistent_model(self):
        result = demo_testnet(blocks=5, difficulty=1, timeout=30, mode="neural-v2")
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["protocol"], "neural-v2")
        self.assertTrue(result["model_digest"])
        self.assertEqual(sum(result["balances"].values()), 5 * REWARD)
        self.assertEqual(result["chain_height"], 5)


if __name__ == "__main__":
    unittest.main()
