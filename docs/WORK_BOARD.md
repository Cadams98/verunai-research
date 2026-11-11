# Verunai agent work board — initial tasks (v0.7)

Status: **unassigned until user starts Codex/Claude sessions**.

| Task | Assigned agent | Priority | Expected artifact |
| --- | --- | --- | --- |
| Reproduce baseline and accelerated neural-v3 candidate mining | Codex | P0 | `benchmarks/` experiment, test suite, explanation |
| Independently review training shortcut and verifier asymmetry | Claude security-auditor | P0 | Findings with severity, proof, mitigations |
| Study fork-choice and signed transaction replay edge cases | Claude consensus-engineer | P1 | Reproducible attack cases or reasoned limitations |
| Run test suite and verify agent configuration | Test engineer | P1 | Exact commands, pass/fail logs, new regression tests |
| Specify and measure RTX 5070 backend parity | Claude ML researcher + owner | P1 | CPU/GPU benchmark on owner's computer, validation correctness |
| Analyze power economics without price hype | Claude token-economist | P2 | Sensitivity model after P0 research |

## Merge gate

Do not merge consensus-related work until the owner sees (1) summary of changed protocol assumptions, (2) negative tests, (3) independent security review, and (4) evidence confirming the claimed results. Mainnet, live token issuance and economic promotion are not authorized.

## Quality gate on every task

Every agent must comply with `docs/ENGINEERING_STANDARDS.md`: produce a small readable diff, tests, updates to corresponding living documentation in the same PR, and explicit resource/security implications. No undocumented protocol change may merge.

## Safety review tasks (new, not started)

| Task | Assigned role | Priority | Expected artifact |
| --- | --- | --- | --- |
| Make model/data provenance and consent checklist | Claude safety-reviewer + ML researcher | P0 | Traceable checklist and dataset/model cards |
| Threat-model neural training data poisoning and reward gaming | Security auditor + safety-reviewer | P0 | Negative tests and documented mitigations |
| Propose source-cited, corrigible public knowledge interface | Safety-reviewer + ML researcher | P1 | Design RFC, citations and uncertainty evaluations |
| Define meaningful community oversight and incident response | Human owner + outside contributors | P1 | Public governance RFC with appeal and rollback plan |

Never present any of these tasks as completed before independent review and reproducible evidence.
