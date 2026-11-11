"""Checks for the v0.8 P0 three-node harness, its relay, and process metrics.

Unit tests are deterministic. The integration tests start real node processes on
127.0.0.1; their block contents vary between runs, but every assertion is an
invariant (convergence, independent audit, clean shutdown) that must always hold.
"""

import os
import socket
import threading
import unittest
from dataclasses import replace
from unittest.mock import patch

from verunai import testnet_harness as harness
from verunai.neural_v3 import LedgerChain, mine_ledger
from verunai.process_metrics import pid_alive, sample_process
from verunai.testnet_proxy import CountingRelay
from verunai.wallet import ADDRESS_RE, address_from_public_hex


class TestHarnessPlanning(unittest.TestCase):
    """Deterministic configuration, validation and comparison helpers."""

    def test_plan_is_reproducible_from_the_seed(self):
        config = harness.TrialConfig(seed=7)
        self.assertEqual(harness.plan_trial(config), harness.plan_trial(config))
        self.assertNotEqual(harness.plan_trial(config),
                            harness.plan_trial(replace(config, seed=8)))
        plan = harness.plan_trial(config)
        self.assertEqual(sorted(plan.launch_order), [0, 1, 2])
        self.assertTrue(all(ADDRESS_RE.fullmatch(miner) for miner in plan.miners))
        self.assertEqual(len(set(plan.miners)), 3)

    def test_legacy_protocol_labels_are_valid_miner_ids(self):
        for protocol in ("bigram-v1", "neural-v2"):
            plan = harness.plan_trial(harness.TrialConfig(seed=3, protocol=protocol))
            for miner in plan.miners:
                self.assertRegex(miner, r"\A[A-Za-z0-9_-]{1,40}\Z")

    def test_out_of_range_controls_are_rejected(self):
        bad = ({"nodes": 2}, {"nodes": 6}, {"difficulty": 0}, {"difficulty": 4},
               {"target_height": 1}, {"timeout": 1}, {"protocol": "neural-v9"},
               {"sync_interval": 0}, {"seed": -1}, {"node_difficulty_overrides": {5: 1}})
        for changes in bad:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(harness.TrialConfig(seed=1), **changes).validate()

    def test_convergence_requires_one_head_at_target_height(self):
        same = [{"head": "a", "height": 5}] * 3
        self.assertTrue(harness.converged(same, 5))
        self.assertFalse(harness.converged(same, 6))
        self.assertFalse(harness.converged(same[:2] + [{"head": "b", "height": 5}], 5))
        self.assertFalse(harness.converged([], 1))

    def test_ledger_fingerprint_verifies_and_comparison_finds_disagreement(self):
        chain = LedgerChain(1)
        miner = address_from_public_hex("11" * 32)
        for _ in range(2):
            mine_ledger(chain, miner)
        exported = chain.export()
        fingerprint = harness.ledger_fingerprint("neural-v3", exported)
        self.assertEqual(fingerprint["height"], 2)
        self.assertEqual(fingerprint["balances"], {miner: 100})
        self.assertEqual(harness.compare_fingerprints([fingerprint, dict(fingerprint)]), [])
        altered = {**fingerprint, "balances": {miner: 150}}
        self.assertEqual(harness.compare_fingerprints([fingerprint, altered]), ["balances"])
        tampered = {**exported, "blocks": [{**exported["blocks"][0], "reward": 500}]}
        with self.assertRaises(ValueError):
            harness.ledger_fingerprint("neural-v3", tampered)

    def test_summary_counts_failures_and_uses_nearest_rank(self):
        self.assertEqual(harness._nearest_rank([1, 2, 3, 4], 95), 4)
        self.assertEqual(harness._nearest_rank([5], 50), 5)
        summary = harness.summarise_campaign([
            {"result": "FAIL", "failure_kind": "not_converged"},
            {"result": "FAIL", "failure_kind": "not_converged"},
        ])
        self.assertEqual(summary["failures_by_kind"], {"not_converged": 2})
        self.assertEqual(summary["passed"], 0)
        self.assertIsNone(summary["converged_s"])


class TestRelayAndMetrics(unittest.TestCase):
    """The relay counts bytes exactly and never alters them."""

    def test_relay_counts_bytes_in_both_directions(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)

        def echo_twice():
            connection, _ = server.accept()
            with connection:
                data = connection.recv(1024)
                connection.sendall(data * 2)

        thread = threading.Thread(target=echo_twice, daemon=True)
        thread.start()
        relay = CountingRelay(server.getsockname()[1])
        port = relay.start()
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
                client.sendall(b"verunai")
                client.shutdown(socket.SHUT_WR)
                received = b""
                while chunk := client.recv(1024):
                    received += chunk
            self.assertEqual(received, b"verunaiverunai")
            thread.join(timeout=5)
            for _ in range(50):
                if relay.counts()["bytes_from_node"] == 14:
                    break
                threading.Event().wait(0.02)
            counts = relay.counts()
            self.assertEqual((counts["bytes_to_node"], counts["bytes_from_node"]), (7, 14))
            self.assertEqual(counts["connections"], 1)
        finally:
            relay.stop()
            server.close()

    def test_relay_rejects_invalid_targets(self):
        for port in (0, 70000):
            with self.subTest(port=port), self.assertRaises(ValueError):
                CountingRelay(port)

    def test_process_metrics_report_values_or_an_explicit_reason(self):
        self.assertTrue(pid_alive(os.getpid()))
        sample = sample_process(os.getpid())
        if sample["source"] == "unavailable":
            self.assertTrue(sample["unavailable_reason"])
        else:
            self.assertGreater(sample["cpu_seconds"], 0)
            self.assertGreater(sample["peak_rss_bytes"], 0)


class TestThreeNodeProcesses(unittest.TestCase):
    """Real OS processes on loopback: convergence, audits and shutdown invariants."""

    def assert_no_survivors(self, record):
        self.assertTrue(record["pids"], "trial should have launched processes")
        self.assertEqual([pid for pid in record["pids"] if pid_alive(pid)], [])

    def test_three_v3_nodes_converge_and_pass_independent_audits(self):
        record = harness.run_trial(harness.TrialConfig(seed=101, difficulty=1, target_height=3,
                                                       timeout=60))
        self.assertEqual(record["result"], "PASS", record.get("failure_detail"))
        self.assertEqual(len(record["audits"]), 3)
        self.assertTrue(all(audit["cli_audit"] == "VALID" for audit in record["audits"]))
        self.assertGreaterEqual(record["ledger"]["height"], 3)
        self.assertEqual(sum(record["ledger"]["balances"].values()), 50 * record["ledger"]["height"])
        self.assertGreater(record["network_total_bytes"], 0)
        self.assert_no_survivors(record)

    def test_legacy_protocols_still_converge_unchanged(self):
        for protocol in ("bigram-v1", "neural-v2"):
            with self.subTest(protocol=protocol):
                record = harness.run_trial(harness.TrialConfig(
                    seed=202, protocol=protocol, difficulty=1, target_height=2, timeout=60))
                self.assertEqual(record["result"], "PASS", record.get("failure_detail"))
                self.assert_no_survivors(record)

    def test_mismatched_difficulty_is_reported_as_divergence(self):
        record = harness.run_trial(harness.TrialConfig(
            seed=303, difficulty=1, target_height=2, timeout=6,
            node_difficulty_overrides={2: 2}))
        self.assertEqual(record["result"], "FAIL")
        self.assertEqual(record["failure_kind"], "not_converged")
        self.assert_no_survivors(record)

    def test_unexpected_harness_error_still_stops_every_node(self):
        with patch.object(harness, "_fetch_status", side_effect=RuntimeError("injected fault")):
            record = harness.run_trial(harness.TrialConfig(seed=404, difficulty=1,
                                                           target_height=2, timeout=20))
        self.assertEqual(record["failure_kind"], "harness_error")
        self.assertIn("injected fault", record["failure_detail"])
        self.assert_no_survivors(record)


if __name__ == "__main__":
    unittest.main()
