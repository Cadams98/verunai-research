# Two-agent research assignment for Verunai v0.7

> This document is a handoff for agents run by the project owner. It does NOT mean any agent has been started or the tasks have been completed.

## ChatGPT / Codex — work-factor attacker

Goal: honestly test whether a miner can shortcut v3 training by exploiting the linear gradient's algebraic structure. Formally derive the deterministic model update from `verunai/neural_consensus.py`; create at least two valid block-candidate implementations (canonical and attacker-optimized); benchmark candidate throughput on CPU and, if available, NVIDIA CUDA with full correct block validation; report speedup, storage tradeoff, and precomputation requirements. Do not change protocol rules just to improve the benchmark. Include deterministic regression tests. Target: a reproducible comparison proving the limits of the current protocol.

Acceptance criteria: independent v3 validator accepts the optimized candidate's blocks, baseline and optimized measurements published, 100% test pass rate, no unsubstantiated claim of secure proof of useful work.

## Claude Code — independent security and protocol audit

Goal: inspect `docs/SECURITY_FINDINGS_V06.md`, Ed25519 transaction handling, mempool admission, chain replay, fork choice, network requests, and gradient commitment. Threat-model malformed JSON, front-running, replay, resource exhaustion, fork/reorg losses, miner reward substitution and invalid model updates. Produce concrete exploit tests and propose high-priority mitigations. Do not add real-money wallets or public node exposure.

Acceptance criteria: attack cases are reproducible against v0.6; findings classified by severity; every critical issue has a test and a design recommendation; preserve protocol version and old export compatibility.

## Shared project rules

- Source of truth is the GitHub repository after the owner publishes it. Until then, use the extracted release folder.
- Create separate branches / pull requests. Don't let competing agents overwrite each other's changes.
- No active coin offering, mainnet, founder premine, promises of returns, or token sales.
- Keep the project open-source and public-benefit oriented.
- Signatures and existing tests do not establish consensus safety.
- The next important milestone is **cheaper verification than production and meaningful AI work**; wallets are not the hard problem.
