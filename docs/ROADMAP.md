# Roadmap and proposed GitHub issues

## Milestone 0 — research baseline (complete in this starter)
- [x] A deterministic AI-related candidate update is hashed into each block.
- [x] More simulated attempts per round raise block-winning opportunities.
- [x] Replayer rejects fake model updates, forged rewards, and modified blocks.
- [x] Accepted blocks update shared model state and fictional balances.
- [x] Specialist Claude Code agent instructions documented.

## Milestone 0.5 — two-process localhost testnet (completed v0.4)
- [x] Independent operating-system mining processes (not merely simulated miner weights).
- [x] Explicit peer links, block relay, peer-tip polling, fully verified chain synchronization.
- [x] Deterministic demo fork choice, persistence with validated restore, and read-only status endpoints.
- [x] Scripted two-process acceptance test, honest/tampered chain tests, and new protocol threat model.
- [x] Optional PyTorch CPU/CUDA neural-training benchmark harness (CPU version executed; **user RTX 5070 not yet tested**).
- [ ] Cryptographically authenticated peers and signed miner identities: **NOT completed**.
- [ ] Proof of genuinely useful AI work resistant to shortcuts: **NOT completed**.
- [ ] Secure global consensus and real token economics: **NOT completed**.

## Milestone 0.6 — signed TEST payments and neural-v3 network (completed v0.6)
- [x] Disposable Ed25519 research wallets with public-key-derived addresses.
- [x] Signed account transfers with sequence-based replay protection, transaction fees and atomic state changes.
- [x] Two independent OS processes mining and confirming a transfer; independent chain/model replay.
- [x] Tests for forged signatures, altered amounts/fees, replay, double spending, insufficient balance and fraudulent AI gradient commitments.
- [x] Reproducible fake-header cost asymmetry audit.
- [ ] Secure private-key storage and authenticated public-network consensus: **NOT completed**.

## Milestone 1 — protocol research (next)
- [ ] Threat model: adversarial GPU miner, precomputation, model poisoning, easy shortcuts.
- [ ] Compare at least 3 candidate useful-work tasks using a measurement table.
- [ ] Bench the task on CPU vs NVIDIA GPU; report actual work/energy/second.
- [ ] Establish independent deterministic/reproducible cross-device verification.
- [ ] Derive and test difficulty adjustment proposal across varying aggregate power.
- [ ] Specify reward schedule and how supply is audited.

**Exit criterion:** show a reproducible, adversarially tested AI task that miners cannot profitably bypass and validators can check more cheaply than miners compute.

## Milestone 2 — local GPU prototype
- [ ] Implement bounded GPU task with PyTorch or equivalent.
- [ ] Benchmark RTX 5070 and at least one second GPU class; measure VRAM, watts if available, and throughput.
- [ ] Implement verifiable model updates to a held-out evaluation target.
- [ ] Establish a protocol version, data availability, and model checkpoint scheme.

## Milestone 3 — secure multi-host private testnet
- [x] Signed TEST transactions and disposable fake-coin wallets (v0.6); **miner networking identity remains unauthenticated**.
- [ ] Multiple independent processes/nodes on a local/private network.
- [ ] Block propagation, chain sync, fork resolution, replay protection.
- [ ] DoS controls, malicious peers, tamper testing, model poisoning defenses.
- [ ] Dashboard for observed effective throughput and block distribution.

## Milestone 4 — economics and security
- [ ] Conservative miner operating cost analysis and network reward sensitivity.
- [ ] Validate whether paid AI workload demand covers compute expenses.
- [ ] Independent cryptography and distributed systems audit.
- [ ] Legal/compliance review before any public coin, sale, or investment claim.

**Build rule:** do not market token value, accept deposits, or announce a mainnet before the exit criteria are reached.

## Humanity-first release gates

Before any public model, data ingest or hosted application launch, satisfy the model safety, privacy, provenance, source quality, abuse testing, red-team and incident-response criteria in `docs/SAFETY_AND_ETHICS.md` and `docs/SAFETY_TEST_PLAN.md`. A permissionless blockchain alone cannot enforce those policies across other operators. Keep a transparent record of unresolved harms and community feedback.
