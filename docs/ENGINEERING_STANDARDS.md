# Verunai engineering standards (required)

**Applies to:** human contributors, Codex, Claude Code, delegated subagents, research scripts, and protocol releases. **Purpose:** keep code readable, maintainable, and scalable, with documentation maintained as part of every meaningful change. These standards apply to the existing v0.6 research prototype, not a claim that it already meets every target.

## Fifth rule: Organized file and package structure

**4. Organized repository and clear module ownership:** Place each file in the directory defined by `docs/FOLDER_STRUCTURE.md`. No miscellaneous root files, unowned packages, duplicated utilities, or circular imports. Proposed module moves need an import-compatibility plan, updated docs, and tests. The layout checker enforces basic hygiene; architectural boundaries require review.

## The three detailed technical pillars

### 1. Readable: optimize for the next person reading the code
- Use descriptive names that explain *what a value represents*; spell out specialized terminology the first time it appears in nearby docs.
- Prefer a small, purpose-specific function over a large routine. A function near 40–60 lines deserves review; a module approaching 400–500 lines deserves a decomposition proposal. These are review triggers, not arbitrary hard limits.
- Keep consensus logic explicit. Avoid clever one-liners, hidden side effects, deeply nested control flow, and surprising mutable global state.
- Add type annotations for new or substantially changed public functions. Document invariants, input limits, and failure modes; comments explain *why*, not every obvious operation.
- Use meaningful, specific exceptions. Don't swallow exceptions or silently accept malformed input. Do not log secrets.
- **Do not rewrite functional code solely to satisfy style guidelines without tests and an owner-approved plan.**

### 2. Manageable: change one thing safely at a time
- Keep responsibilities separated: protocol validity, cryptographic operations, training calculations, ledger rules, networking, CLI, and tests.
- Make small pull requests (PRs): one problem, acceptance criteria, tests, docs, and a migration note when necessary.
- Do not create parallel implementations that silently disagree. Version serialization and consensus-breaking changes; preserve legacy research experiments intentionally.
- Treat all untrusted data and peer messages as hostile. Enforce byte, time, memory, and rate limits in designs and tests.
- Dependencies require a stated reason, compatible version constraints, and documented security/licensing implications. Never commit secrets, real funds, or uncontrolled mining daemons.
- Each confirmed bug gets a regression test; each feature gets tests for both legitimate and malicious/invalid input.

### 3. Scalable: design for many independent participants, measure first
- Favor clear module interfaces and measurable bottlenecks over premature micro-optimization.
- Record CPU/GPU cost, memory use, input/output sizes, network overhead, validation cost, and effects of increasing node count when relevant.
- Specify whether a benchmark is single-process, two-process localhost, LAN, or distributed on real machines. Never extrapolate network scaling from a localhost demo.
- Do not put floating-point values into consensus-sensitive state without a demonstrated cross-platform determinism plan; define canonical bytes and integer/range limits.
- Define resource budgets and bounded work for peers. Distinguish model usefulness from mining speed. Validate security claims independently.
- Never ship a consensus change based only on a happy-path test or a single GPU benchmark.

## Documentation is part of the feature, not a later task

For every functional change, update the relevant documents **in the same PR**:

| Change | Required documentation | Required testing/evidence |
| --- | --- | --- |
| Protocol, block, consensus, reward, or wallet | `docs/PROTOCOL.md` or versioned protocol document; new Architecture Decision Record (ADR) for changed assumptions | Deterministic test vectors, invalid cases, replay, security review |
| Networking, node API, storage | `docs/ARCHITECTURE.md` and operations guide (`docs/PRIVATE_TESTNET.md`) | Failure, timeout, malformed-peer, synchronization tests |
| AI model, training, GPU backend | ML protocol/benchmark document and measurement setup | Baseline, reproducible metrics, CPU parity when relevant |
| User-facing command or setup | `README.md` or dedicated quickstart | Exact working command(s), tested environment |
| New module or responsibility shift | `docs/ARCHITECTURE.md` | Unit and integration tests |
| Bug fix, behavior change, or performance improvement | Relevant document + `CHANGELOG.md` when observable | Regression test or before/after measurement |

**Always** document assumptions, limitations, and known security gaps. For no-behavior refactors, explain how behavior was preserved. For documentation-only updates, no code tests are required unless a command was changed.

## Required PR handoff

Every coding agent must provide:
1. **Problem and boundaries:** what is being changed and what is explicitly out of scope.
2. **Design overview:** relevant modules and why this approach is simpler or more correct than alternatives.
3. **Changed code:** readable, typed where appropriate, scoped to the task.
4. **Tests:** exact commands and actual pass/fail/skip results. Never invent test results.
5. **Documentation:** links to the docs updated **in the same change**, or a justified `documentation-only/no behavior change` exception.
6. **Scalability and security:** resource impact, validation work, attack surfaces, unresolved risks.
7. **Review:** independent adversarial review for consensus/security-sensitive changes before merge.

## Preferred development loop (for people learning as they build)

1. Reproduce the existing behavior; identify its invariants.
2. Explain the proposed change in plain language (the *why*).
3. Change the smallest responsible module.
4. Add tests that demonstrate success **and** a failure mode.
5. Run tests and benchmarks; report the measured facts.
6. Update the README, architecture/protocol references, and decision log in the same PR.
7. Review the diff for clarity and document what was learned.

## Baseline debt, not hidden

The current v0.6 prototype includes large mixed-responsibility modules (for example `verunai/network.py` and the CLI entrypoint) and lacks production-grade consensus proofs. Future work should extract transport, validation, and orchestration behind documented interfaces **incrementally**, keeping existing tests passing. This policy is a target and review checklist, not a claim that all code already satisfies it.

## Highest-priority requirement: Ethical and safe AI for humanity

Read `docs/SAFETY_AND_ETHICS.md` and `docs/SAFETY_TEST_PLAN.md` before proposing changes to model training, shared knowledge, mining incentives, data ingestion, interfaces, or agent privileges. Include a safety impact assessment in every pull request: affected people, privacy/consent, foreseeable misuse, data/model provenance, energy and accessibility implications, mitigations, and what remains untested. For purely mechanical changes, explain why these risks do not change. Safety is a **release gate**, not an afterthought, and independent human review is required for high-impact changes. Static policy checks cannot substitute for behavioral evaluation.
