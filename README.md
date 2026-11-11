# VERUNAI — public-interest AI mining research

**Founded by Christian Adams (2026).**  
**Motto:** *Built by everyone. Verified by anyone.*  
**Status:** Open-source, experimental research prototype — not a public blockchain or tradable coin.

**Start here (Windows):** [Setup and first run](docs/START_HERE_WINDOWS.md).  
**Founder and community stewardship:** [Project stewardship](docs/PROJECT_STEWARDSHIP.md) and [Founding principles](docs/FOUNDING_PRINCIPLES.md).


> **AI agent setup:** This release also includes Codex/Claude Code project instructions, seven preconfigured Claude subagents, a Windows setup checker, and starter prompts. See [Windows agent setup](docs/AGENT_SETUP_WINDOWS.md), [copy/paste prompts](docs/AGENT_START_PROMPTS.md), and the [work board](docs/WORK_BOARD.md). These files do not launch autonomous agents or a live cryptocurrency by themselves.


**Built by everyone. Verified by anyone.**

> **Engineering policy:** All contributors and AI agents must follow [Engineering Standards](docs/ENGINEERING_STANDARDS.md). Read the [Folder Structure](docs/FOLDER_STRUCTURE.md) and [Architecture Map](docs/ARCHITECTURE.md), [Architecture Decisions](docs/decisions/0001-readable-modular-documented.md), and [Changelog](CHANGELOG.md). Changes require clear code, tests, and **documentation in the same pull request**. The standards do not imply the prototype is production-ready.



## Repository organization

Keep code, tests, documentation, evidence, and agent definitions in their designated locations. See the [v0.6.2 organization milestone](docs/milestones/MILESTONE_V062_REPORT.md). See [Folder Structure](docs/FOLDER_STRUCTURE.md) and run `python scripts/check_repository_layout.py` before submitting changes. The Python package is not yet reorganized into feature subpackages; future refactors will be staged with tests.

## Milestone achieved: cryptographically signed TEST transfers across two neural-mining nodes (v0.6)

**New `neural-v3` experiment:** Ed25519 wallet identities, signature-verified fictional TEST payments, transaction fees paid to miners, replay protection via sender sequence numbers, mempool broadcasting, block inclusion and deterministic replay. This v3 ledger uses the same small, integer-exact model-training challenge as v2; v1/v2 remain available. **These are research-only funds, not real cryptocurrency.**

Quick-start (Python 3.10+, new dependency required):

```bash
python -m pip install -e .
python -m verunai demo-ledger-process
python -m unittest discover -s tests -v
```

The full demo uses **two independent operating-system processes**. Alice mines 50 TEST, signs a transfer of 12 TEST plus a 1 TEST fee to Bob, Bob mines the confirmation block, and both nodes independently verify the payment and resulting AI model. The balances are Alice 37 TEST and Bob 63 TEST, with 100 TEST total issuance from two blocks. The private signing keys are disposable and never printed by the demo.

On Windows: double-click `RUN_V3_LEDGER_DEMO_WINDOWS.bat`. See [v0.6 milestone report](docs/milestones/MILESTONE_V06_REPORT.md), [v3 protocol and usage](docs/NEURAL_V3_LEDGER.md), and [security findings](docs/SECURITY_FINDINGS_V06.md).

**Limitations:** This is not secure permissionless consensus, public AI, mainnet, or a production wallet. SHA-256 still chooses winners; validators re-execute the small AI computation, enabling possible disproportionate verification costs. The computation is not proven essential or efficient. Model-training usefulness remains an open research problem.

## Previous milestone: integer-exact neural training across two nodes (v0.5)

**New experiment:** A separate versioned `neural-v2` blockchain now binds block candidates to a real, deterministic single-layer neural-network training step (two dense matrix multiplications, a gradient calculation, and an integer weight update). Independent peers redo the winning training step, check its gradient commitment and model-state commitment, reject altered data, and reconstruct matching model states on replay. Version 1 remains available and unchanged for compatibility.

**Run the neural-mining two-process demonstration:**

```bash
python -m verunai demo-testnet --protocol neural-v2 --blocks 5 --difficulty 1
```

**Run a simulation that saves and independently audits its blocks:**

```bash
python -m verunai mine --protocol neural-v2 --difficulty 1 --blocks 10 --powers 1,2 --output neural-chain.json
python -m verunai audit neural-chain.json
```

**Measure how much work miners and validators perform:**

```bash
python -m verunai neural-mining-benchmark --attempts 150 --backend python
```

For an optional PyTorch backend, try `--backend torch-cpu` or, on a correctly configured NVIDIA GPU, `--backend torch-cuda`. This uses float64 GPU operations and is **not optimized for consumer GPUs**; it is a correctness experiment, not a promise of faster mining. Validator nodes still use canonical integer Python arithmetic. GPU parity on your RTX 5070 has not been tested here.

On Windows, double-click `RUN_NEURAL_TESTNET_WINDOWS.bat` to run the v2 two-process demonstration. See [v0.5 report](docs/milestones/MILESTONE_V05_REPORT.md), [neural-v2 protocol](docs/NEURAL_V2_PROTOCOL.md), and [GPU setup](docs/GPU_BENCHMARK.md).

**Proof status: no secure useful-work consensus yet.** A miner might find cheaper ways to produce valid candidate results; the protocol still selects winners with SHA-256 and validators rerun the expensive computation. This is not a production blockchain, a coin launch, or an investment product. This is meaningful research progress, not proof that the core cryptographic problem is solved.

## Previous milestone: two independent local testnet nodes (v0.4)

This release adds **two real operating-system processes**, each with an independent in-memory chain and optional saved chain file, connected through local HTTP. Nodes independently mine, relay blocks, replay and verify peer chains, resolve short forks using an explicit demo rule, and converge on a common head. The original v0.4 test suite ran 17 tests; v0.5 expands coverage to at least 30 test cases, with optional CUDA tests skipped where unavailable.

**Try the actual two-process demonstration:**

```bash
python -m verunai demo-testnet --blocks 8 --difficulty 2
```

It launches two localhost nodes, mines eight fictional reward blocks, verifies that both processes converge, replays their saved chains independently, prints winners and balances, and shuts them down. This is *not* a real public, trustless or money-bearing blockchain. The blocks use SHA-256 proof of work; their bound AI updates are a toy statistical task.

### Run nodes manually in two terminals

Terminal A:

```bash
python -m verunai node --miner alice --port 8101 --peer http://127.0.0.1:8102 --mine --difficulty 2 --max-blocks 20 --storage alice.json
```

Terminal B:

```bash
python -m verunai node --miner bob --port 8102 --peer http://127.0.0.1:8101 --mine --difficulty 2 --max-blocks 20 --storage bob.json
```

In another terminal:

```bash
python -m verunai status --url http://127.0.0.1:8101
python -m verunai audit alice.json
```

To stop a node press Ctrl+C. The HTTP service binds to **127.0.0.1** by default and is NOT suitable for exposure to the public Internet. `--allow-lan` only acknowledges that risk; it does not provide security. See [private testnet guide](docs/PRIVATE_TESTNET.md) and [attack surface](docs/ATTACK_SURFACE.md).

### Real neural-network training benchmark (separate from mining)

If PyTorch is installed, run:

```bash
python -m verunai gpu-benchmark --device auto --steps 30 --width 128 --batch 64
```

This runs a small neural network through real gradient descent, reporting the device, training speed, and training loss. It is **not** yet part of the mining challenge, and floating-point numerical differences across GPUs make it unsuitable as a consensus rule without further research. See [GPU instructions](docs/GPU_BENCHMARK.md).

---


Our vision is a community-supported, publicly accessible, source-citing AI and permissionless compute network. This is a research prototype, not a launched coin. Read [Founding Principles](docs/FOUNDING_PRINCIPLES.md) before contributing.

*VERUNAI is a provisional project name; trademark and domain checks are not complete.*

> **Not a cryptocurrency, not production consensus, and not a secure public network or GPU miner.** The prototype now uses real separate-process local networking, but it has no secure peer identities, independent economic security, or verifiable useful-AI-work consensus. TEST rewards are fictional and cannot be traded or spent.

## Vision

Computers compete to find blocks. To attempt each block, a miner has to compute a valid nonce-dependent machine-learning update. The winning block records the model update and awards coins. Stronger machines should win more frequently if they can calculate more valid candidates per unit time. Eventually, model training and model inference could create demand for useful network computation. The long-term public-benefit mission must not depend on exclusive company control.

## Try it now (Python 3.10+, no dependencies)

From the project directory:

```bash
python -m verunai mine --blocks 5 --difficulty 2 --powers 1,2,5 --output chain.json
python -m verunai audit chain.json
python -m unittest discover -s tests -v
python -m verunai benchmark --attempts 2000
```

- `--powers 1,2,5` simulates three miners attempting 1, 2, and 5 candidate updates per *round*. These are **not measured GPU speed ratios**.
- The first candidate whose SHA-256 commitment begins with the specified number of zero hex digits wins the block.
- For every nonce, the miner generates and hashes a reproducible mini-batch for a small next-character prediction model.
- A validator recomputes the winning AI update, verifies the hash target, and only then issues 50 fictitious `TEST` units.
- Each accepted update increases the counts for the tiny character-level statistical model; its training-data cross-entropy is reported as a rough learning demonstration.
- `chain.json` contains a replayable ledger with blocks and simulated winner balances.

## How it works

1. The previous block hash fixes the next challenge's parent.
2. Each miner chooses an ID and a nonce.
3. The pair `(parent_hash, miner_id, nonce)` deterministically selects a mini-batch of next-character examples from a fixed public corpus.
4. The miner computes the mini-batch transition counts (a small, meaningful model update).
5. The miner commits to the update and block details by hashing the canonical block payload.
6. If the commitment meets the demo target, the block is proposed.
7. A validator redoes that one mini-batch update, verifies the hash and chain link, and appends the block.
8. The ledger adds a fixed reward to the winning miner and the shared model incorporates the update.

## What this does **not** prove

- It does not solve trustless useful-work consensus: an optimized miner might exploit shortcuts, and a production protocol would require economic/security analysis and independent peer review.
- It does not train a neural network or large language model. It trains a small character transition model.
- The original `mine` mode uses one Python process and simulated round-robin attempts. The new `node` mode uses real independent processes, but still CPU-based fake-work mining and no demonstrated GPU mining fairness.
- Most nonwinning computations are discarded; protocol changes are needed to harvest their value safely.
- It has basic explicit-peer HTTP networking, persistence, fork resolution, and chain synchronization, but **not** secure peer authentication, production-safe wallets, real-value transactions, difficulty retargeting, Sybil resistance, a capped issuance curve, public-network hardening, or real token value.
- Recomputing one tiny update is cheap **relative to the many tries miners perform**, but scaling this to meaningful GPU AI training is an open engineering/research problem.

## Open-source development

This starter includes an MIT license, a GitHub Actions test workflow, contribution/security guidance, and agent collaboration plan. To publish it, create a public GitHub repository and upload these files. Public source code is **not** evidence of a valuable token or cryptographically secure consensus.

- `docs/FAST_TRACK.md`: 48-hour, 7-day, 14-day, and 30-day research milestones.
- `docs/AGENT_WORKFLOW.md`: paste-ready tasks for Codex, Claude Code, and security review.
- `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`: public-contribution baseline.
- `python -m verunai benchmark`: local CPU candidate/verification baseline (not GPU and not proof of useful work).

## Agent setup

- `CLAUDE.md`: shared rules that Claude Code loads in this project.
- `.claude/agents/`: specialist Claude Code agents with defined roles. Ask Claude Code to use each by name.
- `AGENTS.md`: instructions for ChatGPT/Codex or any other development agent.
- `docs/START_WITH_CLAUDE.md`: a ready-to-paste first task to run with Claude.
- `docs/PROTOCOL.md`: current toy protocol and why it isn't yet a secure consensus protocol.
- `docs/ROADMAP.md`: build order and acceptance checks.

Claude Code installation: <https://code.claude.com/docs/en/overview>. Agents docs: <https://code.claude.com/docs/en/sub-agents>.

## High-level progression

1. **Local prototype + independent-process localhost testnet (this package)** — verified toy AI work bound to proof-of-work, gossip/sync, competing forks, auditable persisted chains.
2. **Real GPU AI task** — deterministic or verifiably reproducible neural computation, objective benchmarks, cost measurement.
3. **Independent validation** — audit sampling / succinct proofs / fraud proofs as appropriate, adversarial testing.
4. **Private multi-machine testnet** — extend localhost HTTP to authenticated/secure multi-host transport; add secure identities and transaction protocol.
5. **Economic viability** — demand from AI services, hardware costs, emission policy, regulatory analysis.
6. **Public release only after independent security review.**

## Safety

Do not publish a publicly tradable token or ask anyone to dedicate significant paid GPU time based on this prototype. Do not store real financial value or connect a wallet to it.

## Ethics and safety: our highest priority

**Verunai is intended to serve all humanity.** Human rights, user safety, privacy, truthful knowledge, accessibility, community accountability, and responsible energy use take priority over token value or speed. Read `docs/SAFETY_AND_ETHICS.md`, `docs/SAFETY_TEST_PLAN.md`, and [ADR 0003](docs/decisions/0003-humanity-first-safety.md). These are binding development policies, **not** evidence that this experimental prototype has passed an AI safety evaluation. A new `safety-reviewer` Claude subagent can independently review changes, but human accountability remains essential.
