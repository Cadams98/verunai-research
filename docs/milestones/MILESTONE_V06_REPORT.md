# VERUNAI Milestone v0.6 — signed TEST payment network

**Built by everyone. Verified by anyone.**

**Result: Complete for a controlled local research prototype.** No public cryptocurrency or mainnet exists.

## What is working

1. **Two independent operating-system mining nodes** communicate over loopback HTTP with signed TEST transfers embedded in neural-gradient mining blocks.
2. **Ed25519 disposable wallets** provide signatures tied to public addresses. Sender signatures protect amounts, recipients, fees and transaction sequences.
3. **Fictional account-based TEST ledger** validates balances, prevents basic replay/double-spending, and pays the block subsidy and transaction fees to winning miners.
4. **Atomic validation:** Invalid transfers and forged training commitments cannot change balances or model weights. Independently re-importing the block history validates state from genesis.
5. **Backward compatibility:** v1 and neural-v2 remain as their own modes. A versioned v3 chain cannot be mistakenly replayed as v2.
6. **Runnable demonstrations:** `demo-ledger`, `demo-ledger-process`, `wallet-new`, `send-test`, `audit`, and `security-audit` are included, with Windows launchers.

## Reproduced experiment

Run: `python -m verunai demo-ledger-process`. Actual result stored in `evidence/v06_two_process_signed_payment.json`.

| Metric | Measured outcome |
|---|---|
| Independent Python processes | 2 |
| Neural-v3 blocks accepted | 2 |
| Signed transfers confirmed | 1 |
| Alice initial mining reward | 50 TEST |
| Alice transfer / fee | 12 / 1 TEST |
| Alice final balance | 37 TEST |
| Bob final balance | 63 TEST |
| Network issuance | 100 TEST |
| Same block hash, same model digest | Yes |
| Full historical replay | Passed |
| Real-value coins | **None** |

The protocol rewards are nontransferable outside the educational ledger and have no monetary or market value.

## Automated test outcome

Run: `python -m unittest discover -s tests -v`.

- **45 tests discovered**
- **44 passed**
- **1 skipped:** Requires actual NVIDIA CUDA GPU
- Runtime in the supplied execution environment: approximately 11–12 seconds

See `evidence/v06_test_results.txt`. Tests exercise fraudulent signatures, modified recipients, double spending, replay attempts, wrong sequence numbers, bad issuance rewards, forged neural gradients, wrong protocol versions, state persistence, peer sync, and actual OS-process node execution.

## Key negative result — currently a blocker

Run: `python -m verunai security-audit --samples 50`. The benchmark in `evidence/v06_security_audit.json` demonstrated that a miner can cheaply manufacture a block header satisfying hash difficulty while providing **false gradient data**. Validators must recompute the neural training work to reject it.

In one local CPU run, fake headers took around **0.068 ms** each to grind while validating each forged header took around **1.68 ms**. That is approximately **25x more validation effort** per forged header. These figures depend on CPU and test difficulty and are not broad performance estimates. This is a practical warning that **cheap independent proof verification remains unsolved**.

This release does **not** establish that the AI computation is essential to winning. The current gradient is mathematically structured, based on a small fixed corpus and subject to caching/precomputation attacks. Bitcoin-like economic security has not been demonstrated.

## Remaining major work

- Prove, through research and independent review, a meaningful useful-work consensus scheme with cheap verification.
- Benchmark actual RTX 5070 hardware and cross-device numerical agreement.
- Develop an open public knowledge model and transparent, licensed training-data governance.
- Implement real peer-to-peer security, hardened consensus, difficulty adjustment, robust forks, network recovery, model poisoning defenses, economics, and formal third-party audits.
- Launch the public GitHub repository and invite independent protocol research. No repository has been created or updated by this release.

**Release position:** Useful for technical contributors and transparent experimental demonstrations. Unfit for real funds, financial promises, public mining, or untrusted Internet traffic.
