"""UW-1 deterministic protocol regressions (large sweeps are opt-in)."""
from dataclasses import replace
from hashlib import sha256
import unittest
from unittest.mock import patch

from verunai.useful_work.challenge import Parameters, check, sample
from verunai.useful_work.commitment import DIGEST_SIZE, HEADER_SIZE, UPDATE_BOUND, encode, parse
from verunai.useful_work.evaluation import evaluate_steps
from verunai.useful_work.experiments import _toy_grinding, perturb, with_gradient
from verunai.useful_work.prover import canonical_prover, optimized_prover, updated
from verunai.useful_work.task import (DIMENSIONS, GRADIENT_BOUND, RESIDUAL_BOUND,
                                     WEIGHT_BOUND, held_out, make_task, training_pool)
from verunai.useful_work.transcript import Transcript, replay
from verunai.useful_work.verifier import Verifier


class UsefulWorkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = make_task(16, "task", "alice", "0" * 64, 1)
        cls.honest = canonical_prover(cls.task)
        cls.packet = encode(cls.task, cls.honest)
        cls.params = Parameters(8, 1)
        cls.probe = ((1,) + (0,) * 15,)

    def rejected(self, result):
        packet = encode(self.task, result)
        with patch("verunai.useful_work.verifier.sample", return_value=self.probe):
            self.assertFalse(Verifier(self.task, self.params).submit(packet).accepted)

    def test_honest_provers_and_replay(self):
        self.assertEqual(self.honest, optimized_prover(self.task))
        self.assertEqual(parse(self.task, self.packet).result, self.honest)
        for params in (self.params, Parameters(), Parameters(64, 2)):
            t = Verifier(self.task, params).submit(self.packet)
            self.assertEqual(t, Transcript.from_bytes(t.to_bytes()))
            self.assertTrue(replay(self.task, self.packet, Transcript.from_bytes(t.to_bytes()), t.digest))
        self.assertEqual(updated(((0, 0),), ((-3, 3),), 2), ((1, -1),))

    def test_a1_gradient_unit_errors(self):
        for delta in (-1, 1):
            g = perturb(self.honest.gradient, {(0, 0): delta})
            self.rejected(with_gradient(self.task, self.honest, g))

    def test_a2_residual_gradient_consistent_but_wrong(self):
        e = perturb(self.honest.residual, {(0, 0): 1})
        g = perturb(self.honest.gradient, {(i, 0): v for i, v in enumerate(self.task.x[0])})
        result = with_gradient(self.task, replace(self.honest, residual=e), g)
        t = check(self.task, result, self.params, self.probe)
        self.assertFalse(t[0])
        self.assertNotEqual(t[1][0][0], t[1][0][1])
        self.assertEqual(t[1][0][2], t[1][0][3])

    def test_a3_zero_and_stale_gradient(self):
        zero = tuple((0,) * 16 for _ in range(16))
        stale = canonical_prover(make_task(16, "task", "alice", "0" * 64, 0)).gradient
        for gradient in (zero, stale):
            self.rejected(with_gradient(self.task, self.honest, gradient))

    def test_a4_a5_b6_context_replay(self):
        for identifier, assignee, head, seed in (
            ("other", "alice", "0", 1), ("task", "bob", "0", 1),
            ("task", "alice", "1", 1), ("task", "alice", "0", 2),
        ):
            other = make_task(16, identifier, assignee, head * 64, seed)
            with self.assertRaisesRegex(ValueError, "domain or task"):
                Verifier(other).submit(self.packet)

    def test_a7_malformed_oversized_and_bounds(self):
        result = replace(self.honest, residual=perturb(self.honest.residual, {(0, 0): 2 * RESIDUAL_BOUND}))
        malformed = (bytearray(self.packet), self.packet[4:], self.packet + b"x" * 1_000_000,
                     self.packet[:50], encode(self.task, result))
        with patch("verunai.useful_work.verifier.sample") as draw:
            for packet in malformed:
                with self.assertRaises(ValueError):
                    Verifier(self.task).submit(packet)
            draw.assert_not_called()

    def test_framing_and_digest_fail_before_integer_decode(self):
        bad_digest = self.packet[:-1] + bytes([self.packet[-1] ^ 1])
        with patch("verunai.useful_work.commitment._sections") as sections:
            for packet, error in ((self.packet + b"x", "length"), (self.packet[:-1], "length"),
                                  (bytearray(self.packet), "type"), (b"x" + self.packet[1:], "domain"),
                                  (bad_digest, "commitment")):
                with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                    parse(self.task, packet)
            sections.assert_not_called()

    def test_signed_section_boundaries_with_valid_digest(self):
        d = self.task.dimension
        residual_cells = len(self.task.x) * d
        body = self.packet[:-DIGEST_SIZE]
        for cell, bound in ((0, RESIDUAL_BOUND), (residual_cells, GRADIENT_BOUND),
                            (residual_cells + d*d, UPDATE_BOUND)):
            for sign in (-1, 1):
                for excess in (0, 1):
                    offset = HEADER_SIZE + 4 * cell
                    encoded = (sign * (bound + excess)).to_bytes(4, "big", signed=True)
                    modified = body[:offset] + encoded + body[offset + 4:]
                    packet = modified + sha256(modified).digest()
                    with self.subTest(cell=cell, sign=sign, excess=excess):
                        if excess:
                            with self.assertRaisesRegex(ValueError, "bounds"):
                                parse(self.task, packet)
                        else:
                            self.assertEqual(parse(self.task, packet).digest, packet[-DIGEST_SIZE:])

    def test_evaluation_content_is_disjoint_at_all_dimensions(self):
        for d in DIMENSIONS:
            with self.subTest(dimension=d):
                train = training_pool(d)
                test = tuple(zip(*held_out(d)))
                self.assertTrue(train and test)
                self.assertEqual(len(set(train)), len(train))
                self.assertEqual(len(set(test)), len(test))
                self.assertTrue(set(train).isdisjoint(test))
                self.assertTrue({x for x, _ in train}.isdisjoint(x for x, _ in test))
                task = make_task(d, "scope", "alice", "0" * 64, 42)
                self.assertLessEqual(set(zip(task.x, task.y)), set(train))

    def test_provers_against_independent_scalar_reference(self):
        for d in DIMENSIONS:
            weights = tuple(tuple(WEIGHT_BOUND if (i + 3*j) % 5 else -WEIGHT_BOUND
                                  for j in range(d)) for i in range(d))
            task = make_task(d, "oracle", "alice", "0" * 64, 456, weights)
            n = len(task.x)
            residual = tuple(tuple(sum(task.x[i][a] * weights[a][j] for a in range(d))
                                   - task.y[i][j] for j in range(d)) for i in range(n))
            gradient = tuple(tuple(sum(task.x[a][i] * residual[a][j] for a in range(n))
                                   for j in range(d)) for i in range(d))
            expected = tuple(tuple(weights[i][j] - (-1 if gradient[i][j] < 0 else 1)
                                   * (abs(gradient[i][j]) // task.divisor)
                                   for j in range(d)) for i in range(d))
            for prove in (canonical_prover, optimized_prover):
                with self.subTest(dimension=d, prover=prove.__name__):
                    result = prove(task)
                    self.assertEqual((result.residual, result.gradient, result.weights),
                                     (residual, gradient, expected))
                    self.assertTrue(Verifier(task).submit(encode(task, result)).accepted)

    def test_a8_exact_weight_update(self):
        self.rejected(replace(self.honest, weights=perturb(self.honest.weights, {(0, 0): 1})))

    def test_a9_one_reward_and_b3_retry_limit(self):
        verifier = Verifier(self.task)
        self.assertTrue(verifier.submit(self.packet).reward_eligible)
        with self.assertRaisesRegex(ValueError, "already"):
            verifier.submit(self.packet)
        wrong = with_gradient(self.task, self.honest, perturb(self.honest.gradient, {(0, 0): 1}))
        verifier = Verifier(self.task, self.params, limit=2)
        with patch("verunai.useful_work.verifier.sample", return_value=self.probe):
            for expected in (1, 2):
                t = verifier.submit(encode(self.task, wrong))
                self.assertEqual(t.attempt, expected)
                self.assertFalse(t.reward_eligible)
        with self.assertRaisesRegex(ValueError, "exhausted"):
            verifier.submit(self.packet)

    def test_a10_correct_but_no_improvement(self):
        evidence = evaluate_steps()
        self.assertEqual(len(evidence["steps"]), 50)
        worsened = [s for s in evidence["steps"] if s["worsened"]]
        self.assertTrue(worsened)
        self.assertTrue(all(s["correct"] and s["label"] == "no improvement" for s in worsened))

    def test_a6_b1_b2_preview_counterfactual_and_fresh_sampling(self):
        toy = _toy_grinding(150)
        self.assertEqual(toy["fixed"]["accepted"], 30)
        self.assertEqual(toy["preview"]["accepted"], 90)
        # A fixed wrong relation can pass on its kernel; a different challenge rejects it.
        wrong = with_gradient(self.task, self.honest, perturb(self.honest.gradient, {(0, 0): 1}))
        kernel = ((0, 1) + (0,) * 14,)
        self.assertTrue(check(self.task, wrong, self.params, kernel)[0])
        self.assertFalse(check(self.task, wrong, self.params, self.probe)[0])

    def test_b4_invalid_duplicate_and_zero_challenges(self):
        for vectors in (((0,) * 16,), ((256,) * 16,), ((True,) * 16,),
                        ((-1,) * 16,), ((1,),), ()):
            with self.assertRaises(ValueError):
                check(self.task, self.honest, self.params, vectors)
        with self.assertRaises(ValueError):
            check(self.task, self.honest, Parameters(), self.probe * 2)
        with self.assertRaises(ValueError):
            Parameters(8, 2)
        with patch("verunai.useful_work.challenge.secrets.token_bytes",
                   side_effect=[bytes(64), bytes([1]) * 64, bytes([1]) * 64, bytes([2]) * 64]):
            first, second = sample(16, Parameters())
        self.assertNotEqual(first, second)
        self.assertTrue(all(first) and all(second))

    def test_b4_sampler_exhaustion_fails_closed_after_commitment(self):
        verifier = Verifier(self.task, self.params, limit=1)
        with patch("verunai.useful_work.challenge.secrets.token_bytes", return_value=bytes(16)) as rng:
            with self.assertRaisesRegex(RuntimeError, "fresh challenges"):
                verifier.submit(self.packet)
            self.assertEqual(rng.call_count, 128)
        with self.assertRaisesRegex(ValueError, "exhausted"):
            verifier.submit(self.packet)

    def test_b5_tampered_transcript_and_replacement_digest(self):
        t = Verifier(self.task, self.params).submit(self.packet)
        for altered in (replace(t, accepted=False), replace(t, attempt=True),
                        replace(t, challenges=self.probe if t.challenges != self.probe else ((2,) * 16,))):
            with self.assertRaises(ValueError):
                replay(self.task, self.packet, altered, t.digest)
        replaced = replace(t, session="f" * 32)
        replaced = replace(replaced, digest=sha256(replaced.body()).hexdigest())
        with self.assertRaises(ValueError):
            replay(self.task, self.packet, replaced, t.digest)
        self.assertTrue(replay(self.task, self.packet, replaced, replaced.digest))

    def test_b6_commit_before_randomness_and_modified_payload(self):
        verifier = Verifier(self.task, self.params)

        def draw(d, params):
            self.assertEqual(verifier._commitments, [(1, self.packet[-32:])])
            return self.probe

        with patch("verunai.useful_work.verifier.sample", side_effect=draw):
            t = verifier.submit(self.packet)
        mutated = self.packet[:-33] + bytes([self.packet[-33] ^ 1]) + self.packet[-32:]
        with self.assertRaisesRegex(ValueError, "commitment"):
            replay(self.task, mutated, t, t.digest)
        # Even with a valid new commitment, replay must bind the original packet.
        rehashed = mutated[:-32] + sha256(mutated[:-32]).digest()
        with self.assertRaises(ValueError):
            replay(self.task, rehashed, t, t.digest)


if __name__ == "__main__":
    unittest.main()
