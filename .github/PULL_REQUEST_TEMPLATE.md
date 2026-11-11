## What is changing, and why?
<!-- One focused task; name the affected module(s), constraints, and acceptance criteria. -->

## Design and readable-code review
- [ ] Names, control flow, type annotations, and error handling are understandable to a new contributor
- [ ] Responsibilities are separated; no avoidable large new module or tightly coupled behavior
- [ ] Existing protocol/version behavior is preserved or intentionally versioned

## Repository layout and ownership
- [ ] New files follow `docs/FOLDER_STRUCTURE.md`, with no generated root clutter
- [ ] Dependencies follow the documented direction; no unreviewed cross-package imports
- [ ] Any moved module has updated imports, tests and architecture docs (or not applicable)
- **New or moved file paths:**

## Tests and reproducibility
- [ ] Relevant passing and failing tests are included with exact commands and results
- [ ] Invalid/adversarial cases are tested where relevant
- [ ] Benchmarks state hardware, parameters, and comparisons, or are marked not applicable

## Documentation updated in this PR
- [ ] README/usage instructions updated if commands or user behavior changed
- [ ] Architecture/protocol/ADR updated when interfaces or consensus assumptions changed
- [ ] CHANGELOG updated for observable changes, or reason for omission documented
- **Changed documentation files:**
- **Explanation if documentation is not needed:**

## Security and scalability
- **Limits/bottlenecks/verification costs:**
- **Threats and unknowns:**
- [ ] Consensus/security changes reviewed independently (or not applicable)

## Review status
- **Agent/author:**
- **Owner approval required before merge:** Yes

> Read `docs/ENGINEERING_STANDARDS.md` before submitting. No tests, docs, or performance claims may be fabricated.

## Humanity-first safety and ethics (required)
- **People who may benefit or be harmed, including non-users:**
- **Personal data, consent, retention and deletion implications (or not applicable):**
- **Potential misuse, model/data poisoning, misinformation and tool permissions:**
- **Fairness, multilingual access and accessibility implications:**
- **Compute/energy impact (measured, unknown, or not applicable):**
- **Controls, residual risks, evidence and documentation updated:**
- [ ] Read `docs/SAFETY_AND_ETHICS.md` and `docs/SAFETY_TEST_PLAN.md`
- [ ] Independent safety review for changes to model/data, agent authority, miner training or public interfaces (or documented not applicable)
- [ ] Stop-ship risks identified and addressed or release explicitly blocked
