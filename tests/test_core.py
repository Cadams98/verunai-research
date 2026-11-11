import copy
import unittest
from dataclasses import replace
from verunai.core import Chain, make_candidate, mine_round_robin, training_batch, REWARD, VOCAB
from verunai.benchmark import benchmark


class TestMining(unittest.TestCase):
    def test_cpu_benchmark_smoke(self):
        result = benchmark(20, verify_samples=3)
        self.assertEqual(result["candidate_attempts"], 20)
        self.assertGreater(result["candidates_per_second"], 0)
        self.assertGreaterEqual(result["median_validation_milliseconds"], 0)

    def test_deterministic_training_task(self):
        task = training_batch("0" * 64, "miner1", 3)
        self.assertEqual(task, training_batch("0" * 64, "miner1", 3))
        self.assertEqual(sum(n for _, _, n in task), 48)
        self.assertTrue(all(0 <= a < VOCAB and 0 <= b < VOCAB for a,b,n in task))

    def test_mining_and_replay(self):
        chain = Chain(difficulty=1)
        initial_loss = chain.cross_entropy()
        for _ in range(8):
            block, attempts = mine_round_robin(chain, {"fast": 4, "slow": 1})
            self.assertTrue(block.hash.startswith("0"))
            self.assertGreater(attempts, 0)
        self.assertLess(chain.cross_entropy(), initial_loss)
        replay = Chain.import_and_verify(chain.export())
        self.assertEqual(replay.head, chain.head)
        self.assertEqual(replay.balances, chain.balances)
        self.assertEqual(sum(replay.balances.values()), 8 * REWARD)
        self.assertEqual(replay.counts, chain.counts)

    def test_reject_tampered_ai_work(self):
        chain = Chain(difficulty=1)
        block, _ = mine_round_robin(chain, {"alice": 1})
        bogus_updates = ((0, 0, 48),)
        if block.updates == bogus_updates:
            bogus_updates = ((0, 1, 48),)
        invalid = replace(block, updates=bogus_updates)
        with self.assertRaisesRegex(ValueError, "AI work verification failed"):
            Chain(1).accept(invalid)

    def test_reject_modified_reward_and_hash(self):
        chain = Chain(difficulty=1)
        block, _ = mine_round_robin(chain, {"alice": 1})
        with self.assertRaisesRegex(ValueError, "Wrong issuance"):
            Chain(1).accept(replace(block, reward=9999))
        with self.assertRaisesRegex(ValueError, "Tampered block hash"):
            Chain(1).accept(replace(block, hash="0" * 64))

    def test_reject_forged_chain_export(self):
        chain = Chain(1)
        mine_round_robin(chain, {"alice": 1})
        data = copy.deepcopy(chain.export())
        data["blocks"][0]["miner"] = "mallory"
        with self.assertRaises(ValueError):
            Chain.import_and_verify(data)

    def test_reject_wrong_parent_or_height(self):
        chain = Chain(1)
        block, _ = mine_round_robin(chain, {"alice": 1})
        with self.assertRaisesRegex(ValueError, "Bad height"):
            chain.accept(block)


if __name__ == "__main__":
    unittest.main()
