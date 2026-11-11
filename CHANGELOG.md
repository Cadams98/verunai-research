# Changelog

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
