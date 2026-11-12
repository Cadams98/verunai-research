"""Deterministic regression tests for the UW-2 proof-of-improvement experiment."""

import json
import unittest
from dataclasses import replace
from hashlib import sha256

from verunai.uw2 import audit
from verunai.uw2.data import CLASSES, FEATURES, Oracle, overlap
from verunai.uw2.experiments import Config, recorded_beacon, run
from verunai.uw2.model import (DELTA_BOUND, ENCODED_SIZE, accuracy_count, add, decode, digest,
                               encode, predict, train_averaged, zero_weights)
from verunai.uw2 import protocol
from verunai.uw2.protocol import (Round, Settlement, commitment, paired_counts,
                                  recompute_arithmetic, submit)
from verunai.uw2.stats import improved, tail_numerator
from verunai.uw2.workers import (honest_update, label_flip_update, mean_update, noise_update,
                                 split_by_features, zero_update)

SALT = b"s" * 16


def beacon_source(label: str):
    return lambda: recorded_beacon("test", label)


class DataAndModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = Oracle(b"uw2-test")
        cls.shard = cls.oracle.training_shard(0, 400)
        cls.delta = honest_update(zero_weights(), cls.shard)

    def test_known_answer_fingerprints_are_portable(self):
        self.assertEqual(sha256(repr(self.shard).encode()).hexdigest(),
                         "e387dc5e1d65c613ab65a1c44658c1b102f6ac3dc1a2efea59574e2cfdc3fc3a")
        self.assertEqual(sha256(encode(self.delta)).hexdigest(),
                         "2dc198a5f5f0d527a123b4ab1f34117d2e862fa93651929548454c929b6d0102")
        self.assertEqual(digest(add(zero_weights(), self.delta)),
                         "b3d2a8265caaebe5a9c8b8095ac88aa79f248f967438712e2000ed0c594517e8")
        batch = self.oracle.evaluation_batch(bytes(32), b"t", 50)
        self.assertEqual(sha256(repr(batch).encode()).hexdigest(),
                         "ab5ceead0edc86b4abbac474794e9dc8c510a571ee97fa221a679bd684e22585")
        self.assertEqual(accuracy_count(add(zero_weights(), self.delta), *self.oracle.test_set(1000)), 619)

    def test_training_evaluation_and_test_data_are_disjoint(self):
        shards = [self.oracle.training_shard(i, 400) for i in range(3)]
        batches = [self.oracle.evaluation_batch(recorded_beacon(i), b"x", 300) for i in range(3)]
        self.assertEqual(overlap(*shards, *batches, self.oracle.test_set(2000)), 0)
        self.assertEqual(overlap(shards[0], shards[0]), 400)  # the check itself detects reuse
        self.assertNotEqual(self.oracle.training_shard(0, 10), Oracle(b"other").training_shard(0, 10))

    def test_oracle_and_model_reject_invalid_inputs(self):
        for bad in ("seed", b"", b"x" * 65):
            with self.assertRaises(ValueError):
                Oracle(bad)
        for call in (lambda: self.oracle.training_shard(-1, 5), lambda: self.oracle.training_shard(0, 0),
                     lambda: self.oracle.evaluation_batch(b"short", b"", 5),
                     lambda: train_averaged(zero_weights(), (), (), 0, 1),
                     lambda: train_averaged(zero_weights(), (), (), 1, 0)):
            with self.assertRaises(ValueError):
                call()

    def test_update_encoding_is_exact_and_bounded(self):
        raw = encode(self.delta)
        self.assertEqual(len(raw), ENCODED_SIZE)
        self.assertEqual(decode(raw), self.delta)
        too_big = ((DELTA_BOUND + 1,) + (0,) * (FEATURES - 1),) + zero_weights()[1:]
        for bad in (raw[:-1], raw + b"x", bytearray(raw), "text"):
            with self.assertRaises(ValueError):
                decode(bad)
        with self.assertRaises(ValueError):
            encode(too_big)
        with self.assertRaises(ValueError):
            add(zero_weights(), too_big)
        self.assertEqual(predict(zero_weights(), self.shard[0][0]), 0)  # ties go to class 0

    def test_helpers_preserve_totals(self):
        pieces = split_by_features(self.delta, 6)
        total = zero_weights()
        for piece in pieces:
            total = add(total, piece)
        self.assertEqual(total, self.delta)
        self.assertEqual(mean_update([self.delta, self.delta]), self.delta)
        self.assertEqual(noise_update(b"a", 5), noise_update(b"a", 5))
        self.assertNotEqual(noise_update(b"a", 5), noise_update(b"b", 5))


class SignTestTests(unittest.TestCase):
    def test_exact_threshold_and_invalid_inputs(self):
        self.assertEqual(tail_numerator(8, 2), 56)
        self.assertTrue(improved(10, 0))      # 2**-10 equals the limit exactly
        self.assertFalse(improved(9, 0))      # 2**-9 exceeds it
        self.assertFalse(improved(10, 1))
        self.assertFalse(improved(500, 500))
        self.assertFalse(improved(0, 0))
        self.assertTrue(improved(5, 0, (1, 16)))
        for bad in ((-1, 0, (1, 1024)), (1, 0, (0, 1)), (1, 0, (3, 4)), (1.0, 0, (1, 1024))):
            with self.assertRaises(ValueError):
                improved(*bad)


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = Oracle(b"uw2-test")
        cls.shards = [cls.oracle.training_shard(i, 400) for i in range(2)]
        cls.honest = honest_update(zero_weights(), cls.shards[0])

    def settle(self, label, submissions, weights=None):
        weights = zero_weights() if weights is None else weights
        round_ = Round(self.oracle, weights, 0, 300, beacon_source=beacon_source(label))
        reveals = {name: submit(round_, name, delta, SALT) for name, delta in submissions.items()}
        round_.close_commitments()
        for name, (update, salt) in reveals.items():
            round_.reveal(name, update, salt)
        return round_, round_.settle(), {n: u for n, (u, _) in reveals.items()}

    def test_honest_update_is_accepted_and_worthless_ones_are_not(self):
        round_, results, reveals = self.settle("mix", {
            "honest": self.honest, "zero": zero_update(),
            "flip": label_flip_update(zero_weights(), self.shards[1])})
        by_worker = {r.worker: r for r in results}
        self.assertEqual(by_worker["honest"].status, "accepted")
        self.assertEqual(by_worker["honest"].score, by_worker["honest"].wins - by_worker["honest"].losses)
        self.assertEqual((by_worker["zero"].status, by_worker["zero"].score), ("rejected", 0))
        self.assertTrue(recompute_arithmetic(round_.record(), self.oracle, zero_weights(), reveals))
        json.dumps(round_.record())

    def test_harmful_correct_procedure_is_rejected_after_a_good_model_exists(self):
        base = add(zero_weights(), self.honest)
        flip = label_flip_update(base, self.shards[1])
        _, results, _ = self.settle("flip", {"flip": flip, "reapplied": self.honest}, base)
        self.assertEqual({r.status for r in results}, {"rejected"})

    def test_commitments_close_before_the_beacon_and_bind_the_worker(self):
        round_ = Round(self.oracle, zero_weights(), 0, 300, beacon_source=beacon_source("order"))
        update, salt = submit(round_, "alice", self.honest, SALT)
        with self.assertRaisesRegex(ValueError, "already committed"):
            submit(round_, "alice", zero_update(), SALT)
        with self.assertRaisesRegex(ValueError, "between"):
            round_.reveal("alice", update, salt)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            round_.commit("mallory", commitment(0, round_.model_digest, "alice", update, salt))
        round_.commit("copier", commitment(0, round_.model_digest, "copier", encode(zero_update()), SALT))
        round_.close_commitments()
        with self.assertRaisesRegex(ValueError, "closed"):
            submit(round_, "late", self.honest, SALT)
        with self.assertRaisesRegex(ValueError, "does not match"):
            round_.reveal("copier", update, salt)  # cannot adopt alice's revealed update
        with self.assertRaisesRegex(ValueError, "does not match"):
            round_.reveal("alice", encode(zero_update()), salt)  # cannot change after the beacon
        self.assertTrue(round_.reveal("alice", update, salt))
        results = {r.worker: r.status for r in round_.settle()}
        self.assertEqual(results, {"alice": "accepted", "copier": "not_revealed"})
        with self.assertRaises(ValueError):
            round_.settle()

    def test_commitment_binds_round_and_model(self):
        update = encode(self.honest)
        base = commitment(0, "a" * 64, "w", update, SALT)
        for other in (commitment(1, "a" * 64, "w", update, SALT), commitment(0, "b" * 64, "w", update, SALT),
                      commitment(0, "a" * 64, "x", update, SALT), commitment(0, "a" * 64, "w", update, b"t" * 16)):
            self.assertNotEqual(base, other)

    def test_malformed_inputs_are_refused(self):
        round_ = Round(self.oracle, zero_weights(), 0, 300, beacon_source=beacon_source("bad"))
        for worker, value in (("", "0" * 64), ("bad name", "0" * 64), ("w", "xyz"), ("w", "A" * 64)):
            with self.assertRaises(ValueError):
                round_.commit(worker, value)
        garbage = b"\x7f" * ENCODED_SIZE  # well-sized but far outside the update bound
        round_.commit("w", commitment(0, round_.model_digest, "w", garbage, SALT))
        round_.close_commitments()
        with self.assertRaises(ValueError):
            round_.reveal("w", garbage, b"short")
        self.assertFalse(round_.reveal("w", garbage, SALT))
        self.assertEqual(round_.settle()[0].status, "invalid_update")
        for kwargs in ({"round_number": -1}, {"batch_size": 10}):
            with self.assertRaises(ValueError):
                Round(self.oracle, zero_weights(), **{"round_number": 0, **kwargs})
        with self.assertRaises(RuntimeError):
            Round(self.oracle, zero_weights(), 0, beacon_source=lambda: b"short").close_commitments()

    def test_arithmetic_recomputation_detects_inconsistent_records(self):
        round_, _, reveals = self.settle("tamper", {"honest": self.honest})
        record = round_.record()
        check = lambda rec, before=zero_weights(), rev=reveals: recompute_arithmetic(
            rec, self.oracle, before, rev)
        self.assertTrue(check(record))
        forged = json.loads(json.dumps(record))
        forged["settlements"][0]["score"] += 1
        self.assertFalse(check(forged))
        self.assertFalse(check({**record, "beacon": "00" * 32}))
        self.assertFalse(check(record, rev={}))
        self.assertFalse(check(record, before=add(zero_weights(), self.honest)))
        self.assertFalse(hasattr(protocol, "replay"))  # the broader name was withdrawn

    def test_arithmetic_recomputation_does_not_authenticate_history(self):
        # A fabricated round that never happened passes when it is internally consistent:
        # invented beacon, invented worker, no commitment ever recorded by a coordinator.
        beacon, fake = bytes(range(32)), "ab" * 32
        update = encode(self.honest)
        after = add(zero_weights(), self.honest)
        wins, losses = paired_counts(zero_weights(), after,
                                     self.oracle.evaluation_batch(beacon, bytes.fromhex(fake), 300))
        fabricated = {"round": 7, "model_before": digest(zero_weights()), "model_after": digest(after),
                      "beacon": beacon.hex(), "batch_size": 300, "alpha": [1, 1024],
                      "settlements": [vars(Settlement("nobody", fake, "accepted", wins, losses, wins - losses))]}
        self.assertTrue(improved(wins, losses))
        self.assertTrue(recompute_arithmetic(fabricated, self.oracle, zero_weights(), {"nobody": update}))

    def test_published_seed_reconstructs_evaluation_data(self):
        # Disjoint is not secret: anyone with the seed rebuilds the batch a worker is scored on.
        round_, results, _ = self.settle("seed", {"honest": self.honest})
        tag = bytes.fromhex(results[0].commitment)
        scored = self.oracle.evaluation_batch(round_.beacon, tag, 300)
        self.assertEqual(scored, Oracle(b"uw2-test").evaluation_batch(round_.beacon, tag, 300))
        self.assertEqual(Oracle(b"uw2-test").test_set(50), self.oracle.test_set(50))
        self.assertNotEqual(Oracle(b"uw2-other").evaluation_batch(round_.beacon, b"x", 50),
                            self.oracle.evaluation_batch(round_.beacon, b"x", 50))

    def test_the_same_material_is_accepted_again_by_a_second_coordinator(self):
        # No persistent state: commitments bind a round and model, not a coordinator instance.
        outcomes = [self.settle("twice", {"honest": self.honest})[1][0] for _ in range(2)]
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(outcomes[0].status, "accepted")

    def test_default_beacon_is_fresh_randomness(self):
        beacons = {Round(self.oracle, zero_weights(), 0).close_commitments() for _ in range(3)}
        self.assertEqual(len(beacons), 3)


class AuditTests(unittest.TestCase):
    def test_score_claims_are_checked_without_full_recomputation(self):
        oracle = Oracle(b"uw2-test")
        weights = add(zero_weights(), honest_update(zero_weights(), oracle.training_shard(0, 400)))
        xs, ys = oracle.evaluation_batch(bytes(32), b"a", 100)
        claimed = audit.scores(weights, xs)
        challenge = audit.draw_challenge()
        self.assertTrue(audit.check_scores(weights, xs, claimed, challenge))
        self.assertEqual(audit.predictions(claimed), [predict(weights, x) for x in xs])
        forged = claimed[:5] + (tuple(v + 1 if i == 2 else v for i, v in enumerate(claimed[5])),) + claimed[6:]
        self.assertFalse(audit.check_scores(weights, xs, forged, (1,) * CLASSES))
        self.assertTrue(audit.check_scores(weights, xs, forged, (1, 1, 0, 1, 1, 1)))  # a blind spot
        for bad in ((claimed[:-1], challenge), (claimed, (0,) * CLASSES), (claimed, (1,))):
            with self.assertRaises(ValueError):
                audit.check_scores(weights, xs, *bad)
        with self.assertRaises(ValueError):
            audit.draw_challenge(7)


class ExperimentTests(unittest.TestCase):
    def test_quick_experiments_are_deterministic_and_keep_data_disjoint(self):
        def strip(report):
            report = json.loads(json.dumps(report))
            report["E7_costs"].pop("timing_ms")
            report["E7_costs"].pop("timing_ratios")
            return report

        first, second = strip(run(Config.quick())), strip(run(Config.quick()))
        self.assertEqual(first, second)
        self.assertEqual(first["data"]["training_shards_and_test_overlap"], 0)
        collaboration = first["E1_collaboration"]
        for condition in ("per_update_honest", "per_update_with_poisoner", "bundle_honest"):
            self.assertEqual(collaboration[condition]["evaluation_overlap_with_training_or_test"], 0)
        self.assertGreater(collaboration["per_update_honest"]["final_true_accuracy"],
                           collaboration["chance_accuracy"] + 0.2)
        nulls = first["E2_null_attacks"]
        for strategy in ("zero", "replay_accepted_update", "label_flip_correct_procedure"):
            self.assertEqual(nulls[strategy]["accepted_at_1_in_16"], 0)
        costs = first["E7_costs"]
        self.assertTrue(costs["forged_score_claim_rejected"])
        self.assertTrue(costs["correct_but_harmful_step"]["recomputation_matches_submission"])
        self.assertFalse(costs["correct_but_harmful_step"]["accepted_by_improvement_test"])
        self.assertNotEqual(strip(run(replace(Config.quick(), seed="other"), ("E7_costs",)))["E7_costs"],
                            costs)


if __name__ == "__main__":
    unittest.main()
