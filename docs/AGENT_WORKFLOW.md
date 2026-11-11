# Two subscriptions, one shared GitHub project

Tools: ChatGPT Plus / Codex and Claude Pro / Claude Code (subject to plan usage limits). One GitHub repo is the source of truth.

## Avoid simultaneous edits

- **Codex / ChatGPT** owns protocol integration and tests on `feat/consensus-tests`.
- **Claude Code** owns GPU research on `research/gpu-workloads`.
- **Security reviewer** produces threat-model markdown and adversarial tests on `review/threat-model`, without silently rewriting consensus.
- Project owner merges pull requests in sequence after tests; never give two agents simultaneous write access to the same branch/file.

## Task for Codex (copy into Codex)

> Read README.md, AGENTS.md, docs/PROTOCOL.md, and docs/FAST_TRACK.md. This is an educational prototype, not a secure coin. Make a new branch. Expand the threat-model-driven unit tests and identify concrete shortcut attacks that may allow a winning block without expensive useful AI work. Do not add real wallets, external payments, tokens for sale, or claims of security. Submit a pull request describing evidence and remaining limitations.

## Task for Claude Code (copy into Claude Code)

> Read CLAUDE.md, docs/PROTOCOL.md, docs/FAST_TRACK.md, and docs/AGENT_WORKFLOW.md. Work on a new research branch. Implement *benchmarks only* for two deterministic candidate machine-learning computations using my NVIDIA GPU when present; include a CPU fallback and clear environment report. Compare honest mining cost with verifier cost and investigate whether the expensive AI computation can be skipped. Do not change consensus or mint real tokens. Submit a pull request with test results and limitations.

## Task for independent security review (Claude or ChatGPT)

> Assume miners are economically adversarial. Review the protocol and identify ways to win without AI computation, game difficulty/rewards, introduce model poisoning, or exploit nondeterministic GPUs. Output a prioritized attack list, reproducible tests, and the minimum evidence required before any public testnet. This is a design review, not a production audit.

## Daily 15-minute owner workflow

1. Read CI results and PR summaries.
2. Pick one blocker for each coding agent.
3. Require passing tests and measurable evidence, not just agent claims.
4. Merge one branch at a time and rerun tests.
5. Update docs/ROADMAP.md with what was *actually* demonstrated.

## Next milestone after v0.4 (scoped agent assignments)

### Codex: secure network protocol proposal
> Review `verunai/network.py`, `tests/test_network.py` and `docs/ATTACK_SURFACE.md`. Write a threat-first RFC for cryptographically bound network IDs, authenticated peer messages, cumulative-work fork choice, incremental syncing, bounded peer connection counts, and deterministic test vectors. Implement only a **separate experimental v2 branch** with adversarial tests. Preserve v1 compatibility for research; do not add valuable coins or payment handling.

### Claude Code: AI mining candidate research
> Measure `verunai/gpu_research.py` on CPU and CUDA if available. Propose three useful ML training or evaluation tasks with a well-defined proof and independent verifier cost, report shortcut attacks, and demonstrate on the GPU. Separate honest computation from SHA-256 hashing. Avoid claims of trustless proof of useful work without adversarial results.

### Independent reviewer: break the mining requirement
> Reimplement a miner that tries to find accepted v1 blocks while minimizing or eliminating actual useful model training. Quantify speedups and explain why v1 does not prove useful AI work. Independently replay all example blocks and review fork/reorg assumptions. File a reproducible issue for every failure.
