# 0005 — Supervised engineering automation

**Status:** proposed.

VERUNAI needs independent PR feedback and consistent engineering handoffs.
Unattended agents that execute proposed code with publication credentials
combine untrusted input, external model costs, and repository write access.

Use an owner-labeled Claude review with a trusted checkout, bounded diff,
limited job token, and paid execution disabled by default. Use local
owner-authorized Codex sessions for implementation and a dedicated helper
for draft publication. GitHub branch rules and human approval govern merges.
Use a separate credential-free check for the description.

A hosted Codex agent with write credentials could automate more steps, but
would require an independently reviewed boundary between proposal generation
and publication and a separately authorized billing setup. This proposal
keeps the model review advisory and limits automation to the published PR
workflow. The tradeoff is one owner action to request a hosted review and
another to merge.

The [runbook](../ENGINEERING_AUTOMATION.md) defines setup, evidence, and limits.
