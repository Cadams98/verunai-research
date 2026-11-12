"""Check a small UW-1 Windows known-answer set on every CI interpreter."""
import unittest

from verunai.useful_work.experiments import honest_trials


class UsefulWorkFingerprintTests(unittest.TestCase):
    def test_two_task_manifests_match_windows(self):
        # Seeds 0 and 1 use the same fixture and digest order as the full campaign.
        # This deliberately small check is not the 1,000-task correctness gate.
        expected = {
            16: "2441ffd645cfe23e569d2263f7361fb5f2a293bf9d4305f413bba5d809a0d053",
            64: "96836b1283580a42f738029449edad462b77fecb4e7abdbeeb022c57ce69bef1",
            128: "8a53e1ef1b97fe546b0385fe92c1fc45a5e2667d2c7cef259b32897e537c2f75",
            256: "19263a1779f070635180c33b2b65fb163d4dcbede93383c166449e21dd23a195",
        }
        actual = honest_trials(2)
        for dimension, digest in expected.items():
            with self.subTest(dimension=dimension):
                self.assertEqual(actual[dimension]["accepted_per_backend"], 2)
                self.assertEqual(actual[dimension]["failures"], [])
                self.assertEqual(actual[dimension]["manifest_sha256"], digest)
