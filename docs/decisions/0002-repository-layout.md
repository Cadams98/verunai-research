# ADR-0002: Clear repository layout and staged modularization

- **Status:** Accepted
- **Date:** 2026-11-10
- **Context:** Verunai already has separate package, tests, documentation, and agent folders, but a flat Python package and reports in the repository root will not scale with more contributors.

## Decision

Adopt `docs/FOLDER_STRUCTURE.md` as the authoritative layout and dependency guidance. Move historical release reports to `docs/milestones/`, move the sample chain to `evidence/`, and keep root Windows launchers for accessibility. Add automated root-hygiene and required-directory checks. Leave importable Python modules in place for this patch; use test-backed, incremental migrations later.

## Alternatives

- **Immediate full refactor:** rejected due to consensus and import compatibility risks.
- **No structure guardrails:** rejected because root clutter and mixed-responsibility modules would continue growing.
- **Rigid deep package hierarchy now:** deferred until actual module responsibility boundaries are extracted.

## Consequences

New root-level generated files and release reports are blocked by checks. Human reviewers still have to confirm dependency direction and module responsibilities. No blockchain or wallet protocol behavior changes in this update.
