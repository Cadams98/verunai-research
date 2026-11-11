"""Regression checks for the canonical v3 benchmark fixture."""

from dataclasses import replace
import unittest

from verunai.ledger_benchmark import benchmark_ledger
from verunai.neural_v3 import LedgerChain, mine_ledger
from verunai.wallet import address_from_public_hex


class TestLedgerBenchmark(unittest.TestCase):
    def test_reports_canonical_work_and_replay_at_two_heights(self):
        result = benchmark_ledger(attempts=2, repeats=2, blocks=2)
        self.assertEqual(result["protocol"], "neural-v3")
        self.assertEqual(result["fixture"]["transfers"], 0)
        self.assertEqual(set(result["replay_by_height"]), {"1", "2"})
        candidate = result["canonical_candidate"]
        self.assertEqual(candidate["operations_per_sample"], 2)
        self.assertEqual(len(candidate["samples_ms_per_operation"]), 2)
        self.assertGreater(candidate["peak_traced_bytes_per_sample"], 0)
        self.assertEqual(result["fixture"], benchmark_ledger(1, 2, 2)["fixture"])

    def test_rejects_out_of_range_controls(self):
        for args in ((0, 2, 2), (1, 1, 2), (1, 2, 101)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                benchmark_ledger(*args)

    def test_fresh_validator_rejects_malformed_commitment_then_accepts_original(self):
        source = LedgerChain(1)
        block, _ = mine_ledger(source, address_from_public_hex("00" * 32))
        verifier = LedgerChain(1)
        before = verifier.export()
        with self.assertRaisesRegex(ValueError, "Invalid digest format"):
            verifier.accept(replace(block, gradient_digest="malformed"))
        self.assertEqual(verifier.export(), before)
        verifier.accept(block)
        self.assertEqual(verifier.export(), source.export())
        self.assertEqual(verifier.weights, source.weights)
