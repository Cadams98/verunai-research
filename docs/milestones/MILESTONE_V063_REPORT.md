# v0.6.3 — Humanity-first safety policy milestone

## Delivered
- `docs/SAFETY_AND_ETHICS.md`: project mission, privacy, fairness, safety, citations, data provenance, environmental accountability, decentralized limits, and stop-ship gates.
- `docs/SAFETY_TEST_PLAN.md`: evaluation and adversarial research tasks **not yet completed**.
- `docs/decisions/0003-humanity-first-safety.md`: rationale and deliberate tradeoffs.
- `.claude/agents/safety-reviewer.md`: read-only reviewer.
- Updated agent instructions, contribution guidelines, PR template, security policy, README, architecture docs and CI.
- Added tests checking that the ethics policy and review hooks are present.

## Verification on local CPU environment

- `python scripts/check_project_standards.py`: passed.
- `python scripts/check_repository_layout.py`: passed.
- `python scripts/verify_agent_config.py`: passed, **seven** configured subagents.
- `python -m unittest discover -s tests -q`: **55 tests run, 54 passed, 1 skipped** (GPU-only).

## Important limits

This release adds policies and project checks, **not** a deployed AI safety mechanism, evaluated language model, privacy-preserving runtime, decentralized governance, secure consensus, real mining profits, or a live cryptocurrency. Human review and real-world safety evaluation remain required. Static checks alone do not establish safety or ethical compliance.
