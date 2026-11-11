# Milestone v0.6.2 — repository organization

**Date:** November 10, 2026 (engineering standards release)

## What changed

- Historical milestone reports live in `docs/milestones/`, sample chain under `evidence/`, and runnable walkthroughs under `examples/`.
- Added `docs/FOLDER_STRUCTURE.md` and architecture decision ADR-0002 covering dependency boundaries and incremental migration.
- Implemented a read-only repository layout check integrated with GitHub Actions; agents and pull request instructions reference the organization rules.
- Kept public import paths, Windows batch launchers and consensus-critical modules unchanged.

## Reproducibility

```bash
python scripts/check_repository_layout.py
python scripts/check_project_standards.py
python scripts/verify_agent_config.py
python -m unittest discover -s tests -v
python -m verunai audit evidence/demo_chain.json
python -m verunai demo-ledger-process --timeout 45
```

**Measured in this environment:** 50 passing tests; one CUDA/GPU test skipped; signed payment demonstration and v1 historical chain audit completed successfully. No GPU hardware or real network tested. This is a repository maintenance milestone, not an improvement in blockchain security.
