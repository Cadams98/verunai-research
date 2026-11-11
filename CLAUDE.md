# VERUNAI — Claude Code entrypoint

**Founder:** Christian Adams (2026). Read `docs/PROJECT_STEWARDSHIP.md` for attribution and community stewardship; do not invent a registered company, tradable token, or deployed network.

Read `AGENTS.md`, `docs/SAFETY_AND_ETHICS.md`, `docs/SAFETY_TEST_PLAN.md`, `docs/ENGINEERING_STANDARDS.md`, `docs/FOLDER_STRUCTURE.md`, and `docs/ARCHITECTURE.md` for the shared engineering rules and module boundaries. Every implementation must include appropriate documentation in the same PR. Then read `docs/AGENT_SETUP_WINDOWS.md`, `docs/AGENT_BRIEF_V07.md`, `docs/SECURITY_FINDINGS_V06.md`, and `docs/NEURAL_V3_LEDGER.md` before making changes.

Follow the ownership rules in `AGENTS.md`. Claude defaults to independent review. Only take implementation ownership when the owner explicitly assigns a separate scope and branch. Hosted review is advisory and limited to findings. Local reviewers may use the project specialists within their authorized review scope.

Initial request from owner: have `security-auditor` review the v0.6 neural-v3 mining cost asymmetry and possible short-circuit attacks, have `consensus-engineer` independently review fork choice and replay, and return a prioritized written report with reproducible experiments. Do not launch a public chain or publish financial products.

Commands after installation:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m verunai demo-ledger-process
```

To verify subagents, ask which project agents are available or use the Claude Code agent-list UI/command as supported by your version. Delegate by name such as `security-auditor`. Project subagents are defined in `.claude/agents/`.

Use a dedicated `claude/*` branch for changes, and leave `main` untouched until human review. Do not fabricate GPU benchmarks, external verification, or security guarantees.

For public-model, data, knowledge, miner-training or agent-privilege changes, request independent review from `safety-reviewer` in addition to security specialists. Assess privacy, source/consent, misuse, poisoning, community accountability, and whether proposed safeguards can actually operate in a permissionless system. No Claude agent can certify safety or authorize deployment.
