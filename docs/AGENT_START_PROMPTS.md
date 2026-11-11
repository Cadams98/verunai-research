# Copy/paste agent launch prompts

## Prompt for Codex

Read `docs/ENGINEERING_STANDARDS.md`, `docs/ARCHITECTURE.md`, `AGENTS.md`, `docs/AGENT_BRIEF_V07.md`, and `docs/SECURITY_FINDINGS_V06.md`. Be the implementation lead for the v0.7 research experiment. Before edits, propose a scoped plan and use a `codex/shortcut-benchmark` branch. Build a reproducible experiment that measures honest versus algebraically optimized valid neural-v3 block candidates. Check acceptance with the existing independent validator. Add regression tests and report measured throughput, verifier costs, and what could be bypassed. Run the existing tests. Do not assert secure Proof of Useful Work, change issuance rules, launch a real coin, or access real keys.

## Prompt for Claude Code

Read `docs/ENGINEERING_STANDARDS.md`, `docs/ARCHITECTURE.md`, `CLAUDE.md`, `AGENTS.md`, and `docs/AGENT_BRIEF_V07.md`. Identify the subagents in `.claude/agents/`. Delegate the training-shortcut and verifier-asymmetry assessment to `security-auditor` and fork/replay review to `consensus-engineer`. Summarize concrete exploits and exact tests; work read-only at first, without touching Codex's files. Produce a ranked report, clearly separating confirmed vulnerabilities from conjectures.

## Prompt for Claude test-engineer

Use the `test-engineer` subagent to run `python -m unittest discover -s tests -v`, record the exact environment and outcomes, examine v0.6's tests for missing fraud/edge cases, and propose up to five highest-value negative tests. Do not misreport skipped GPU tests as passed.

## Prompt for Codex security remediation (only after the review)

Read the security auditor's concrete findings. Fix exactly one P0/P1 issue on a separate `codex/fix-<issue>` branch, preserve protocol version or explicitly version an incompatible change, write an exploit regression test first, then implement the fix. Run all tests and ask for independent Claude review before merge.
