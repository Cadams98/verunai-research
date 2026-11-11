# ADR-0001: Readability, modularity, scalability evidence, and living documentation

- **Status:** Accepted for Verunai research contributions
- **Date:** 2026-11-10
- **Scope:** All new code, refactors, reviews, agent changes, and documentation

## Context
Verunai is a public-interest project intended to be inspectable by anyone. Consensus and artificial intelligence software are difficult to audit; clever but opaque code or undocumented changes are unacceptable. Existing v0.6 modules need incremental cleanup, but large unreviewed rewrites are risky.

## Decision
Adopt `docs/ENGINEERING_STANDARDS.md`. New work must be readable, split into reviewable responsibilities, supported by tests, and documented in the same PR. New consensus rules require deterministic byte formats, test vectors, an explicit protocol version, and independent security review. Scaling claims require reproducible measurements, not promises.

## Alternatives considered
- **Move quickly and document later:** rejected because undocumented consensus changes make future verification and community participation harder.
- **Rewrite the whole prototype immediately:** rejected because it increases regression risk and slows necessary research.
- **Add rigid complexity limits immediately:** deferred because hard thresholds can encourage artificial code splitting instead of clarity.

## Consequences
Every feature carries a modest up-front documentation/review cost. In return, external contributors can understand decisions, reproduce behavior, and challenge assumptions. Existing debt is to be reduced incrementally with tests.

## Review trigger
Revisit this decision if maintainability metrics or contributor feedback show that the rules are too weak or too burdensome.
