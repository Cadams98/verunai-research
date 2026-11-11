# VERUNAI — shared instructions for Codex and all coding agents

**Founder:** Christian Adams (2026). Follow `docs/PROJECT_STEWARDSHIP.md` for founder recognition and the long-term community-governance intent. Do not equate founder recognition with permanent control over a permissionless network.

## Mission
Research an open-source, permissionless AI network with Bitcoin-inspired competitive mining. This is a public-benefit research project. Verunai v0.6 is a two-process localhost prototype with deterministic neural-update commitments, signed disposable TEST transfers, and basic chain synchronization; it is **not** secure Proof of Useful Work, a public blockchain, a cryptocurrency with value, or a production wallet.

## Engineering standards (non-negotiable)
Read and follow `docs/SAFETY_AND_ETHICS.md`, `docs/SAFETY_TEST_PLAN.md`, `docs/ENGINEERING_STANDARDS.md`, `docs/FOLDER_STRUCTURE.md`, and `docs/ARCHITECTURE.md` before any change. Readable, maintainable, testable, scalable by measured evidence, and documented in the same pull request are release requirements. Include a documentation update or written exception in every task handoff. Never split responsibility ambiguously across agents.

## Required context
Read `README.md`, `docs/NEURAL_V3_LEDGER.md`, `docs/SECURITY_FINDINGS_V06.md`, `docs/AGENT_BRIEF_V07.md`, and `SECURITY.md` before modifying protocol code. For the collaboration process read `docs/AGENT_SETUP_WINDOWS.md` and `docs/WORK_BOARD.md`.

## Non-negotiable safety and accuracy rules
- Never promise coin value, profits, security, or genuine useful-work consensus.
- Don't launch mainnet, deploy a public node, start a real token sale, access third-party systems, or spend money without the owner's explicit approval.
- Do not expose private keys, wallet seeds, API keys, or secrets, including in logs or tests. Use disposable TEST credentials only.
- Preserve compatibility for v1/v2/v3; version any consensus-breaking change explicitly.
- Report separately: (a) cryptographic SHA-256 lottery, (b) actual model computation, (c) verification costs, and (d) the possibility of shortcuts.
- All claims about speed, model quality, and attack resistance need reproducible measurements.
- Never push or merge directly into `main` without owner review. Do not rewrite history or force-push shared branches.
- When changes affect consensus, demand independent adversarial review and negative tests.

## Team roles & branch ownership
- Codex: primary implementation and experiments on `codex/<issue-or-task>` branches.
- Claude Code: independent audit and bounded research on `claude/<issue-or-task>` branches. Its `.claude/agents/` specialists are reviews unless explicitly given a narrow implementation task.
- Human project owner: approves scope, publishes code, and merges reviewed pull requests (PRs).
- Avoid concurrent edits to identical files; use separate Git branches/worktrees or separate sessions.

## Immediate v0.7 research goals
1. Codex: implement an honest baseline-versus-optimized miner experiment and prove whether the optimized candidate bypasses repeated gradient work. Produce a benchmark with exact commands, independent validity checks, and a written explanation of the shortcut.
2. Claude Code security-auditor: independently review v0.6 and add a ranked vulnerability report for expensive validation, replay, fork handling, and network denial-of-service. Never claim an audit is comprehensive.
3. Test engineer: run the current test suite and add a regression test for each confirmed vulnerability.
4. ML researcher: plan CPU-versus-RTX-5070 benchmark with correctness parity and the same training task; do not imply that GPU tests ran until the owner runs them.

## Definition of done for every agent task
A focused, readable diff; passing relevant tests (or disclosed failures); reproducible commands; docs updated in the same PR; architecture/ADR changes if applicable; measured resource/scaling implications; security implications; and an explicit handoff for review. Run `python scripts/check_repository_layout.py`, `python scripts/check_project_standards.py`, and `python -m unittest discover -s tests -v` after installing dependencies.

## Humanity-first decision priority

If speed, token incentives, public access, or model performance conflicts with foreseeable harm, privacy, accountability, or human rights, **escalate** instead of silently optimizing for speed. Require the independent `safety-reviewer` for data/model releases, training updates, and autonomous agent capabilities. The reviewer advises; a human approves any high-impact deployment. Document tradeoffs, dissent, and limitations. Code and document checks are not proof of AI safety.
