# Verunai architecture map — v0.6 research baseline

**Status:** local two-node experimental blockchain, not a deployed permissionless network or secure proof of useful AI work. Update this map when modules or responsibilities change.

The current file map and staged target package layout live in [FOLDER_STRUCTURE.md](FOLDER_STRUCTURE.md).

## Component overview

```text
CLI (`verunai/__main__.py`)
    | launches demos, benchmarks, node processes
    v
Local network + node orchestration (`verunai/network.py`)
    | exchanges blocks, transactions, peer state
    v
Protocol validation and ledger (`verunai/neural_v3.py`)
    | validates signed TEST transfers (`verunai/wallet.py`)
    | calculates and checks model state (`verunai/neural_consensus.py`)
    | verifies block eligibility using hashes
    v
Deterministic chain export/replay + local state
```

Legacy experiments: `verunai/core.py` is v1; `verunai/neural_consensus.py` also defines the v2 chain; v3 adds the signed ledger. Keep these version boundaries explicit.

## Module ownership and contracts

| Module | Current responsibility | Future scaling seam |
| --- | --- | --- |
| `verunai/core.py` | v1 hash/chain and toy-model experiment | Historical compatibility, test vectors |
| `verunai/neural_consensus.py` | Deterministic integer neural step and v2 blocks | Isolate pure training/validation functions |
| `verunai/neural_v3.py` | v3 block structure, ledger state, consensus checks | Separate block validation from storage and orchestration |
| `verunai/wallet.py` | Ed25519 test wallet and signed transfer objects | Key-management boundary and strict canonical transfer encoding |
| `verunai/network.py` | Local HTTP peer networking, mining loops, sync, mempool | Extract bounded transport, sync protocol, mempool, and mining scheduler |
| `verunai/__main__.py` | Command-line entry points for experiments | Thin CLI delegating to tested application services |
| `verunai/gpu_research.py` | Optional CPU/GPU benchmark experiments | Research-only backend, never implicit consensus authority |
| `verunai/ledger_benchmark.py` | Research-only `benchmark_ledger()` and module CLI for canonical v3 work, validation costs, and allocations | Uses the existing validator with local fixtures for accepted blocks and both early and late rejection |
| `verunai/testnet_harness.py` | v0.8 P0: launches 3–5 unmodified nodes as local processes, detects convergence, re-audits saved ledgers | Basis for partition, crash and hostile-peer campaigns (P6); see `docs/TESTNET_HARNESS.md` |
| `verunai/testnet_proxy.py` | Loopback byte-counting relay between harness nodes; forwards bytes unchanged | Becomes the fault-injection proxy (delay, drop, partition) in P6 |
| `verunai/process_metrics.py` | Standard-library CPU-time, peak-memory and liveness readings for child processes | Shared by later observability work (P5) |
| `tests/` | Unit/integration and adversarial regression checks | Add deterministic vectors and multi-host stress tests |

## Protocol invariants to protect

- Independent nodes must validate the same serialized block and model step deterministically.
- A node must reject invalid issuance, signatures, sequence numbers, and model commitments.
- The block hash lottery is **not** proof that the associated neural work was necessary. Do not conflate these operations.
- v1/v2/v3 experiments must not change semantics silently; incompatible future rules require versioned protocols and migration documentation.
- Network-facing code must consider malicious peers and bounded validation cost. Localhost success alone does not establish public-network safety.

## Honest scaling limits

There is no demonstrated multi-host permissionless consensus, secure peer identity, independent economic security, robust persistence under crash/restart, verified profitable GPU mining, or cheaply verifiable useful-training work. These are research milestones, not existing capabilities.

For proposed architectural changes, add a numbered decision record to `docs/decisions/` describing context, alternatives, and validation evidence.

## Safety trust boundaries (design intent only)

Engineering automation runs outside the node runtime. The PR handoff checker
reads GitHub event data, the opt-in Claude action reviews proposed changes,
and the local Codex helper publishes draft PRs from authorized task branches.
See the [engineering automation runbook](ENGINEERING_AUTOMATION.md).

Distinguish consensus validity, miner data/model contributions, model release pipelines, and hosted AI responses. Ledger validators cannot enforce every model output policy on independent peer-operated systems. The model update pipeline will require provenance and poisoning controls before accepting distributed updates; the hosted application layer will require privacy, abuse, and tool-permission safeguards. These are **planned controls**, not existing v0.6.3 runtime features. See `docs/SAFETY_AND_ETHICS.md`.
