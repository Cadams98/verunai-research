# Repository structure and import boundaries

**Status:** accepted organizational standard for v0.6.2. It documents the actual tree and a future target. This is a cleanup-only update: the working Python package deliberately remains at `verunai/` until a separately reviewed migration.

## Current layout (what exists today)

```text
verunai-research/
├── verunai/                 # Importable package and experimental CLI (currently flat)
│   ├── __main__.py          # CLI entry point
│   ├── core.py              # v1 protocol experiment
│   ├── neural_consensus.py  # v2 neural calculations / chain experiment
│   ├── neural_v3.py         # v3 ledger and validation
│   ├── wallet.py            # Test wallet/transaction signatures
│   ├── network.py           # Local HTTP node and syncing
│   └── ...                  # Demos and benchmarks (research-only)
├── tests/                   # Unit, integration, and negative test cases
├── docs/                    # Architecture, protocol, research, agent instructions
│   ├── decisions/           # Accepted architecture decision records
│   └── milestones/          # Historical release reports
├── evidence/                # Reproducible evidence and historical demo chains
├── examples/                # Commands for newcomers and standalone examples
├── scripts/                 # Local development, audit and validation tools
├── .claude/agents/          # Claude subagent specifications
├── .github/workflows/       # Continuous integration test jobs
├── AGENTS.md / CLAUDE.md    # Coding agent contract / entrypoints
├── README.md                # Main project orientation
├── pyproject.toml           # Packaging and dependencies
└── *.bat                    # Windows convenience launchers
```

Root Windows `.bat` files stay in the root for novice usability. Do not put Python logic in batch launchers. Never commit `.venv/`, `__pycache__/`, runtime secrets, generated mining chains, or local benchmarking outputs. Historical demonstration results in `evidence/` are explicitly identified.

## Target module layout (not implemented yet)

```text
src/verunai/
├── blockchain/   # Pure canonical serialization, block/transaction rules, replay
├── mining/       # Challenge generation, candidate search and reward proposal
├── ai/           # Deterministic training reference algorithms and models
├── network/      # Peer protocol, bounded transport and synchronization
├── wallet/       # Signing and transaction authorization
├── storage/      # Persistence and migration
├── cli/          # Thin command-line entrypoints
└── research/     # Reproducible experiments (never consensus authority)
```

Do not create every directory up front or split modules without a demonstrated reason. The target is a responsibility map, not an instruction to rewrite code immediately.

## Ownership rules

| Work | Primary home | Never place in |
| --- | --- | --- |
| Consensus and canonical bytes | `verunai/` today, future `blockchain/` | CLI scripts, network transport |
| Mining challenge/rewards | `verunai/` today, future `mining/` | wallet module |
| Deterministic model updates | `verunai/neural_consensus.py` today, future `ai/` | networking, signing code |
| Peer messages and node lifecycle | `verunai/network.py` today, future `network/` | cryptographic primitives |
| Wallet signature and transfer format | `verunai/wallet.py` today, future `wallet/` | networking handlers |
| Tests | `tests/` | source package or `docs/` |
| Research measurements | `evidence/` for selected snapshots | source or root |
| Design decisions, protocol, history | `docs/` | root unless entrypoint policy |

**Dependency direction:** the CLI invokes application services; networking consumes consensus validation; consensus may call pure mathematical helpers and signature verification; pure helpers must not import the CLI or network. Research code should not become consensus-critical without a new architecture decision and validation. Cyclic imports are forbidden in newly introduced components.

## Naming and change rules

1. Use lowercase `snake_case.py` for modules, meaningful nouns for packages, `test_<feature>.py` for tests, and `NNNN-short-title.md` for architecture decisions.
2. Keep human-oriented root entrypoints few: `README.md`, `AGENTS.md`, `CLAUDE.md`, contribution/security/license files, packaging config, and Windows launcher wrappers. Put new reports under `docs/milestones/` and source-generated evidence under `evidence/`.
3. For every new source module, state its responsibility and public interfaces in `docs/ARCHITECTURE.md`. For every new command, provide an example in the README or `examples/README.md`.
4. Never move protocol files, change import paths, or update canonical serialization as an unreviewed mass rename. First add characterization tests, create a staged migration plan, then migrate one component at a time.
5. Use the structural check: `python scripts/check_repository_layout.py`. It checks hygiene, not architectural quality; human review remains mandatory.

## Planned migration order

- **Stage 1 (this update):** organize reports/examples and enforce structure checks. No import changes.
- **Stage 2:** extract pure deterministic model math behind a stable interface, while preserving vector tests.
- **Stage 3:** extract protocol validation from network orchestration; isolate networking transport.
- **Stage 4:** migrate to `src/verunai/` only after import-path, launcher, test and packaging updates have been tested on Windows and Linux.

A feature should not be merged just because it makes the directory tree prettier. It should make responsibilities clearer while preserving reproducible behavior.

## Ethics/safety file locations

Project-wide commitments live in `docs/SAFETY_AND_ETHICS.md`, safety testing backlog in `docs/SAFETY_TEST_PLAN.md`, and design rationale in `docs/decisions/`. Safety-reviewer agent instructions live in `.claude/agents/`. Actual safety evaluation datasets and synthetic cases should eventually live in `tests/` (private sensitive reports must remain outside the public repository). Do not scatter competing policy documents in root or source packages.
