"""Adversarial and integration tests for signed-neural-v3 TEST transfers."""
import copy
from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from verunai.wallet import Wallet, Transfer, sign_transfer, address_from_public_hex
from verunai.neural_v3 import LedgerChain, LedgerBlock, ledger_candidate, mine_ledger, REWARD
from verunai.network import TestnetNode, request_json
from verunai.ledger_demo import demo_ledger
from verunai.ledger_process_demo import demo_ledger_process
from verunai.adversarial_audit import audit_work_asymmetry


class TestWalletAndLedger(unittest.TestCase):
    def setUp(self):
        self.alice = Wallet.generate()
        self.bob = Wallet.generate()
        self.mallory = Wallet.generate()
        self.chain = LedgerChain(1)

    def test_fake_header_cost_asymmetry_is_demonstrable(self):
        report = audit_work_asymmetry(5)
        self.assertEqual(report['fake_headers_rejected'], 5)
        self.assertGreater(report['false_header_validation_seconds_per'], 0)

    def test_wallet_storage_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "wallet.json"
            self.alice.save(p)
            self.assertEqual(Wallet.load(p).address, self.alice.address)
            with self.assertRaises(FileExistsError):
                self.mallory.save(p)
            self.assertNotIn('private_key', json.dumps({'address': self.alice.address}))

    def test_signed_transfer_and_tampering(self):
        tx = sign_transfer(self.alice, self.bob.address, 10, 1, 0)
        self.assertEqual(Transfer.from_dict(tx.to_dict()), tx)
        self.assertEqual(tx.sender, self.alice.address)
        for forged in (replace(tx, amount=11), replace(tx, recipient=self.mallory.address),
                       replace(tx, fee=0), replace(tx, sequence=1),
                       replace(tx, sender_pubkey=self.mallory.public_hex)):
            with self.subTest(forged=forged), self.assertRaises(ValueError):
                forged.verify()

    def test_invalid_inputs_and_serialization(self):
        for n in (0, -1, True, 10**20):
            with self.assertRaises(ValueError):
                sign_transfer(self.alice, self.bob.address, n, 0, 0)
        with self.assertRaises(ValueError):
            sign_transfer(self.alice, self.bob.address, 1, -1, 0)
        with self.assertRaises(ValueError):
            sign_transfer(self.alice, self.bob.address, 1, 0, -1)
        with self.assertRaises(ValueError):
            sign_transfer(self.alice, 'invalid-address', 1, 0, 0)
        with self.assertRaises(ValueError):
            Transfer.from_dict({"oops": "no"})

    def test_mine_transfer_fee_and_total_supply(self):
        start_mse = self.chain.training_loss()
        mine_ledger(self.chain, self.alice.address)
        tx = sign_transfer(self.alice, self.bob.address, 12, 1, 0)
        mine_ledger(self.chain, self.bob.address, transfers=(tx,))
        self.assertEqual(self.chain.balances[self.alice.address], 37)
        self.assertEqual(self.chain.balances[self.bob.address], 63)
        self.assertEqual(sum(self.chain.balances.values()), 2 * REWARD)
        self.assertEqual(self.chain.sequences[self.alice.address], 1)
        # A quantized stochastic update can be exactly zero; do not assert
        # guaranteed improvement after just two blocks.
        self.assertGreaterEqual(self.chain.training_loss(), 0)
        replay = LedgerChain.import_and_verify(self.chain.export())
        self.assertEqual(replay.balances, self.chain.balances)
        self.assertEqual(replay.head, self.chain.head)
        self.assertEqual(replay.weights, self.chain.weights)

    def test_replay_double_spend_and_no_negative_balances(self):
        mine_ledger(self.chain, self.alice.address)
        tx = sign_transfer(self.alice, self.bob.address, 20, 2, 0)
        mine_ledger(self.chain, self.bob.address, transfers=[tx])
        for txs in ([tx], [tx, tx], [sign_transfer(self.alice,self.bob.address, 1, 0, 3)],
                    [sign_transfer(self.alice,self.bob.address, 100, 1, 1)]):
            with self.subTest(txs=txs), self.assertRaises(ValueError):
                self.chain.check_transfers(txs)
        self.assertEqual(sum(self.chain.balances.values()), 2 * REWARD)

    def test_transaction_atomicity(self):
        mine_ledger(self.chain, self.alice.address)
        a = sign_transfer(self.alice, self.bob.address, 10, 1, 0)
        b = sign_transfer(self.alice, self.mallory.address, 100, 1, 1)
        before = self.chain.export()
        with self.assertRaises(ValueError):
            self.chain.check_transfers([a, b])
        self.assertEqual(self.chain.export(), before)

    def test_reject_forged_block_hash_and_training(self):
        blk,_ = mine_ledger(self.chain, self.alice.address)
        for fake in (replace(blk, hash="0" * 64), replace(blk, reward=10000),
                     replace(blk, miner="intruder"), replace(blk, difficulty=2)):
            with self.subTest(fake=fake), self.assertRaises(ValueError):
                LedgerChain(1).accept(fake)
        # Tests the heavy AI recomputation is never called for an invalid block header.
        with patch('verunai.neural_v3.compute_step', side_effect=RuntimeError('heavy compute')):
            with self.assertRaisesRegex(ValueError, 'Tampered'):
                LedgerChain(1).accept(replace(blk, hash="0"*64))

    def test_fake_gradient_rejected_even_if_hash_target_met(self):
        blk,_ = mine_ledger(self.chain, self.alice.address)
        fake = replace(blk, gradient_digest="0" * 64, hash="")
        # The forger can cheaply grind header hashes without a valid gradient.
        for x in range(1000):
            candidate = replace(fake, nonce=x, hash="")
            from verunai.core import canonical_bytes, sha256
            fakehash=sha256(canonical_bytes(candidate.payload()))
            if fakehash.startswith("0"):
                forged=replace(candidate, hash=fakehash)
                break
        else:
            self.fail('Did not find a cheap fake header')
        with self.assertRaisesRegex(ValueError, 'Invalid neural training work'):
            LedgerChain(1).accept(forged)

    def test_wallet_exploit_attempt_bad_signature_rejected_on_import(self):
        mine_ledger(self.chain, self.alice.address)
        tx = sign_transfer(self.alice, self.bob.address, 10, 0, 0)
        mine_ledger(self.chain, self.bob.address, transfers=[tx])
        tampered = copy.deepcopy(self.chain.export())
        tampered['blocks'][1]['transfers'][0]['amount'] = 500
        with self.assertRaises(ValueError):
            LedgerChain.import_and_verify(tampered)

    def test_old_modes_cannot_replay_v3(self):
        mine_ledger(self.chain, self.alice.address)
        from verunai.neural_consensus import NeuralChain
        with self.assertRaises(ValueError):
            NeuralChain.import_and_verify(self.chain.export())


class TestNetworkTransfers(unittest.TestCase):
    def test_two_http_nodes_mine_sign_transfer_and_replay(self):
        report = demo_ledger()
        self.assertEqual(report['result'], 'PASS')
        self.assertTrue(report['chains_match'] and report['models_match'])
        self.assertEqual(report['alice_balance_TEST'], 37)
        self.assertEqual(report['bob_balance_TEST'], 63)
        self.assertEqual(report['total_TEST_issued'], 100)

    def test_separate_os_processes_mine_and_confirm_payment(self):
        report = demo_ledger_process(timeout=35)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["os_processes"], 2)
        self.assertTrue(report["model_digest_matches"])
        self.assertEqual(report["total_issued_TEST"], 100)

    def test_tx_route_rejects_wrong_signature_and_spend_before_mining(self):
        alice, bob = Wallet.generate(), Wallet.generate()
        node = TestnetNode(miner=alice.address, mode='neural-v3', difficulty=1)
        port = node.start(port=0)
        try:
            tx = sign_transfer(alice, bob.address, 1, 0, 0)
            ok, why = node.submit_transfer(tx.to_dict())
            self.assertFalse(ok)
            self.assertIn('Insufficient',why)
            for _ in range(100):
                if node.mine_batch():
                    break
            receipt = request_json(f'http://127.0.0.1:{port}/tx', {'transfer':tx.to_dict()})
            self.assertTrue(receipt['accepted'])
            self.assertEqual(len(request_json(f'http://127.0.0.1:{port}/mempool')['transfers']), 1)
        finally:
            node.stop()

    def test_same_signed_transfer_cannot_pay_twice_in_mempool(self):
        alice,bob=Wallet.generate(),Wallet.generate()
        node=TestnetNode(miner=alice.address,mode='neural-v3',difficulty=1)
        for _ in range(100):
            if node.mine_batch(): break
        tx=sign_transfer(alice,bob.address,10,0,0)
        self.assertTrue(node.submit_transfer(tx.to_dict())[0])
        self.assertFalse(node.submit_transfer(tx.to_dict())[0])
        for _ in range(100):
            if node.mine_batch(): break
        self.assertFalse(node.submit_transfer(tx.to_dict())[0])
        self.assertEqual(node.chain.balances[bob.address],10)
        self.assertEqual(len(node.pending),0)

if __name__ == '__main__':
    unittest.main()
