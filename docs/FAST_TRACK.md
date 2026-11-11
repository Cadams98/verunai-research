# Fast-track plan: ship research, not a tradable coin

## The thesis

Can permissionless miners compete for Bitcoin-style blocks using expensive AI computation, where the winning proof is cheaply and deterministically verified, the computation makes a model useful, and honest GPU computation is the fastest way to win?

This thesis is **not proven**. Current code is a toy character transition model and a proof-of-work hash commitment that miners could potentially compute more cheaply without doing genuinely useful AI work. An AI-themed hash preimage does not automatically create proof of useful work.

## First 48 focused hours — publish and measure

- Create a **public GitHub repository** (owner selects name; repository publishing is not done automatically by this package).
- Upload the contents of this folder, including `LICENSE`, `.github/workflows/ci.yml`, and agent instructions.
- Run `python -m unittest discover -s tests -v` and `python -m verunai benchmark --attempts 2000`.
- Publish **accurate** README limitations and known failure modes; do not publish a price promise, sell tokens, or connect real wallets.
- Open separate issues for: (a) consensus threat model, (b) 3 candidate useful AI task families, (c) GPU baseline, (d) independent verification, (e) model-training utility, and (f) networking.

## Days 3–7 — measure GPU proof candidates

- ML engineer builds minimal PyTorch GPU workloads for candidate tasks (for example deterministic inference / training updates) on NVIDIA RTX 5070.
- Consensus engineer specifies challenge freshness tied to previous block and input-data availability.
- Security reviewer attempts to get valid block probability without computing expensive ML work.
- Benchmark each task on CPU and GPU: attempts/sec, verifier time, VRAM, reproducibility, energy if measurable, model usefulness, and shortcut cost.
- Put all experiments behind a research feature flag; **do not change consensus rules** to a new AI task until independently reproducible.

## Days 8–14 — competition prototype

- Two real miner processes compete on one host using an isolated local coordinator; do not claim this is peer-to-peer consensus.
- Accept only replay-verifiable blocks. Test fake work, overwritten models, wrong parent, duplicate rewards, bad difficulty, and adversarial inputs.
- Publish one reproducible demonstration video / benchmark report and a candid known-limitations list.

## Days 15–30 — private multi-machine experiment

- Signed identities and an authenticated LAN/private testnet with two independent machines, block propagation, and chain replay.
- Network fault tests and forks before any unauthenticated public participation.
- Public documentation of minimum GPU hardware and measured cost per useful AI job.

## Gate before a public financial token

Require: external security review; meaningful independent verification; actual model quality or customer demand; workable emissions and operating economics; legal review; no hidden insider minting; informed miners. These gates have no guaranteed deadline.

## What success would actually mean

A successful early research demo proves some computational step can be mined, verified, and repeated. It does **not** prove financial value, scalable training, competitive general intelligence, network security, or positive returns to a founder.


## Research milestone v0.4 completed in this package
- Real two-process localhost testnet, deterministic replay and synchronization
- Basic demo fork resolution, persistent local ledgers, status endpoints
- Automated protocol tampering and HTTP negative tests
- Optional PyTorch CPU/CUDA benchmark of real gradient training

**Not achieved:** secure useful-work consensus, GPU-accelerated mining, real coins, public network safety, independent security audit. See `PRIVATE_TESTNET.md` and `ATTACK_SURFACE.md`.
