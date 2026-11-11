# Changelog

## Unreleased - UW-1 audit corrections

- Check exact framing and the packet commitment before integer decoding, while retaining full signed bounds and mathematical checks.
- Split training and evaluation by unique encoded content and version the research task binding.
- Add independent scalar checks, an interleaved CPU and memory benchmark, and portable correctness manifests.

## Unreleased - UW-1 research

- Add a standalone commit-then-challenge matrix verification experiment, exact CPU provers, transcript replay and local attempt limits.
- Record cost, adversarial and held-out evidence; the full correctness gate remains open. Ledger consensus and rewards are unchanged.

## Unreleased — v0.8 P0 three-node testnet harness

- Add `python -m verunai.testnet_harness`. It starts three to five unmodified nodes as separate local processes, waits for convergence, and re-audits every saved ledger in process and with the existing `audit` command.
- Measure convergence time, CPU time, peak memory and node-to-node traffic. Traffic is counted by a loopback relay that forwards bytes unchanged.
- Record 20 neural-v3 and 5 each of bigram-v1 and neural-v2 reference trials as raw evidence (30 of 30 passed). Withdraw the first-seen fork-choice proposal for P3 and recommend most-work with a deterministic lowest-hash tie-break.
- No consensus, fork-choice, networking or storage behaviour changed.

## Unreleased — engineering automation proposal

- Add PR description validation and an owner-authorized Codex draft publisher.
- Propose bounded, opt-in Claude Code PR reviews with paid execution disabled by default.
- Clarify implementation ownership and document authentication, costs, and human merge authority.
- Address the automation audit with a fail-closed handoff check, explicit safety fields, pinned CI actions, and revision-bound Claude reports.
- Remove the PR #3 bootstrap exception and test failing and passing descriptions through the handoff job.

## Unreleased — canonical neural-v3 benchmark

- Added a local benchmark for canonical model computation, candidate generation, block validation, and replay, with timing variability and peak traced Python allocations.
- Measure early format rejection and late neural rejection using deterministic local fixtures. Remove the standalone SHA-256 microbenchmark to avoid comparing a repeated hash with a complete mining attempt.
- Reuse the computed model digest during candidate construction. A historical block regression verifies the candidate hash and fields.
- Added regression checks for the deterministic fixture and canonical validation. Protocol rules and serialization are unchanged.

## v0.6.4 — founder identity and Windows onboarding (2026-11-10)
- Credited **Christian Adams** as Verunai founder (2026) in public-facing project docs, metadata and agent instructions.
- Added project stewardship statement and ADR-0004 distinguishing founder recognition from permanent control.
- Added `docs/START_HERE_WINDOWS.md` and `SETUP_AND_TEST_WINDOWS.bat` for reproducible Windows onboarding.
- Added identity/guide regression checks; no changes to consensus, rewards, or AI training behavior.


This file tracks **observable changes** and research milestones. It does not imply production readiness.

## v0.6.2 — repository layout guardrails (2026-11-10)
- Adopted mandatory folder ownership, naming and dependency rules in `docs/FOLDER_STRUCTURE.md` and ADR-0002.
- Moved historical milestone reports into `docs/milestones/` and the sample chain into `evidence/`.
- Added `examples/README.md`, a read-only layout checker, six regression tests, and continuous integration enforcement.
- Updated Codex/Claude instructions and PR template. No consensus, mining or transaction semantics changed.
- Deferred deeper `src/verunai/` reorganization to independently tested future changes.

## Unreleased — engineering process update (2026-11-10)
- Adopted readable, maintainable, evidence-based scaling standards for all human and AI contributors.
- Added a documented v0.6 architecture map and initial architecture decision record.
- Added a shared PR template, repository-standards checker, and agent handoff rules.
- No mining, block, wallet, reward, or consensus behavior changes.

## v0.6 — research baseline
- Added disposable Ed25519 signed TEST transfers and deterministic v3 ledger replay.
- Demonstrated two separate local processes verifying the same blockchain.
- Known limitations documented in `docs/SECURITY_FINDINGS_V06.md`.

For earlier experimental milestones, see `docs/milestones/MILESTONE_REPORT.md` and `docs/milestones/MILESTONE_V05_REPORT.md`.

## v0.6.3 — Humanity-first ethics and safety policy (docs and checks only)

- Added open, reviewable safety and ethics charter, test backlog and ADR 0003.
- Added read-only `safety-reviewer` Claude agent; human review required before high-impact releases.
- Updated agent, contribution, security, PR, architecture and roadmap instructions to require safety impact assessments.
- Added static policy-presence checks and regression tests. **No model safety mechanism, consensus rule, or public deployment was implemented.**
