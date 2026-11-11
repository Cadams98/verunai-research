"""Regression checks for the canonical v3 benchmark fixture."""

from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from verunai.ledger_benchmark import benchmark_ledger
from verunai.neural_v3 import (
    LedgerBlock, LedgerChain, compute_step, ledger_candidate, mine_ledger, weights_digest,
)
from verunai.wallet import address_from_public_hex


class TestLedgerBenchmark(unittest.TestCase):
    """Check benchmark reporting, rejection stages, and candidate compatibility."""

    def test_reports_canonical_work_and_replay_at_two_heights(self):
        result = benchmark_ledger(attempts=2, repeats=2, blocks=2)
        self.assertEqual(result["protocol"], "neural-v3")
        self.assertEqual(result["fixture"]["transfers"], 0)
        self.assertEqual(set(result["replay_by_height"]), {"1", "2"})
        candidate = result["canonical_candidate"]
        self.assertEqual(candidate["operations_per_sample"], 2)
        self.assertEqual(len(candidate["samples_ms_per_operation"]), 2)
        self.assertGreater(candidate["peak_traced_bytes_per_sample"], 0)
        validation = result["validation_including_chain_init"]
        self.assertEqual(set(validation), {
            "accept_canonical_block",
            "reject_malformed_gradient_digest",
            "reject_neural_mismatch_with_local_state",
        })
        for measurement in validation.values():
            self.assertEqual(len(measurement["samples_ms_per_operation"]), 2)
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
        with patch("verunai.neural_v3.compute_step", wraps=compute_step) as train:
            with self.assertRaisesRegex(ValueError, "Invalid digest format"):
                verifier.accept(replace(block, gradient_digest="malformed"))
            train.assert_not_called()
        self.assertEqual(verifier.export(), before)
        verifier.accept(block)
        self.assertEqual(verifier.export(), source.export())
        self.assertEqual(verifier.weights, source.weights)

    def test_well_formed_block_with_neural_mismatch_recomputes_before_rejecting(self):
        source = LedgerChain(1)
        block, _ = mine_ledger(source, address_from_public_hex("00" * 32))
        verifier = LedgerChain(1)
        verifier.weights[0][0] = 1
        before = verifier.export()
        model_before = weights_digest(verifier.weights)
        with patch("verunai.neural_v3.compute_step", wraps=compute_step) as train:
            with self.assertRaisesRegex(ValueError, "Invalid neural training work"):
                verifier.accept(block)
            train.assert_called_once()
        self.assertEqual(verifier.export(), before)
        self.assertEqual(weights_digest(verifier.weights), model_before)
        self.assertEqual(verifier.balances, {})

    def test_candidate_reuses_digest_and_reproduces_historical_block(self):
        fixture = Path(__file__).resolve().parents[1] / "evidence" / "v06_replayable_signed_chain.json"
        exported = json.loads(fixture.read_text(encoding="utf-8"))
        parent = LedgerChain(exported["difficulty"])
        for entry in exported["blocks"]:
            block = LedgerBlock.from_dict(entry)
            with self.subTest(height=block.height):
                with patch("verunai.neural_v3.weights_digest", wraps=weights_digest) as digest:
                    candidate = ledger_candidate(
                        block.height, parent.head, block.miner, block.nonce, parent.difficulty,
                        parent.weights, block.transfers,
                    )
                    digest.assert_called_once()
                self.assertEqual(candidate, block)
                parent.accept(candidate)
        self.assertEqual(parent.export(), exported)

    def test_tampered_model_commitment_is_rejected_after_genesis(self):
        source = LedgerChain(1)
        miner = address_from_public_hex("00" * 32)
        mine_ledger(source, miner)
        verifier = LedgerChain.import_and_verify(source.export())
        block, _ = mine_ledger(source, miner)
        before = verifier.export()
        model_before = weights_digest(verifier.weights)
        tampered = replace(block, model_digest="0" * 64)
        with patch("verunai.neural_v3.compute_step", wraps=compute_step) as train:
            with self.assertRaisesRegex(ValueError, "Tampered block header"):
                verifier.accept(tampered)
            train.assert_not_called()
        self.assertEqual(verifier.export(), before)
        self.assertEqual(weights_digest(verifier.weights), model_before)
        verifier.accept(block)
        self.assertEqual(verifier.export(), source.export())
