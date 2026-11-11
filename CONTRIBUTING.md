# Contributing to Verunai research

This repository explores experimental AI-compute-bound block mining. It is **not** a secure or valuable cryptocurrency. Do not run it with real funds or promote returns.

## First steps

1. Read `README.md`, `docs/PROTOCOL.md`, `docs/FAST_TRACK.md`, `docs/SAFETY_AND_ETHICS.md`, `docs/SAFETY_TEST_PLAN.md`, `docs/ENGINEERING_STANDARDS.md`, `docs/FOLDER_STRUCTURE.md`, and `docs/ARCHITECTURE.md`.
2. Run `python -m unittest discover -s tests -v` and `python -m verunai benchmark --attempts 1000`.
3. Open an issue explaining a testable hypothesis, measurement, or vulnerability before proposing protocol changes.
4. Make changes on a branch, add tests, and submit a pull request (PR).

## Non-negotiable engineering quality

Code must be readable, manageable, and designed for measurable scalability, with documentation updated in the **same PR**. Use the repository pull request template and document interfaces, assumptions, behavior changes, and known limits. Reviewability is a requirement, not a future cleanup task.

## Pull request checklist

- What changed? How can another person reproduce the result?
- For consensus changes: Are all inputs, outputs, byte encodings, and verification rules deterministic?
- For machine learning (ML) changes: What held-out metric improved and compared with which baseline?
- For mining changes: Can a malicious miner get the same block-winning chance while avoiding the expensive ML work?
- For performance claims: Include environment, GPU model, VRAM, library versions, throughput, verification cost, and power measurement method.
- For rewards: Show supply accounting tests and explain abuse incentives.

Don't submit secrets, copyrighted model weights/data without permission, real wallet keys, misleading claims of profitability, or dangerous code that mines without explicit informed user consent.

## Decision policy

Core protocol changes require at least one implementation review and an independent adversarial/security review. The project owner retains merge decisions. GitHub discussions may propose ideas; an accepted pull request is not an endorsement of economic or security claims.

## File location requirement

Use `docs/FOLDER_STRUCTURE.md` to select the correct directory for new work. Do not add new standalone documentation or generated JSON to the repository root. Run `python scripts/check_repository_layout.py` before opening a pull request. A module relocation requires updated imports, architecture docs, and passing tests.

## Human impact and safety review

All pull requests must complete the Safety and ethics section in `.github/PULL_REQUEST_TEMPLATE.md`. Changes to AI models, training data, shared-model updates, AI interfaces, mining incentives, or agent privileges need a documented threat model and independent `safety-reviewer` assessment. No use of personal data without appropriate consent, permissions and protective handling. Follow `docs/SAFETY_AND_ETHICS.md`; passing automated checks does not establish safety or ethical compliance.
