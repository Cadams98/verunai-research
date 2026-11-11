# Automation safety review for PR #3

## Codex internal self-review

A separate read-only Codex session inspected the proposed workflow, formatter,
PR template, and activation runbook. This was an internal self-review of
Codex-authored work. It did not exercise the hosted provider or provision
credentials.

| Area | Finding and controls |
| --- | --- |
| Authority | A shared GitHub identity cannot separate founder and agent authority. Keep publication attended until a separate identity and server-side restrictions pass positive and negative checks. |
| Privacy and consent | PR diffs and reports can disclose sensitive content. Screen the diff, confirm provider and retention suitability, use an environment-scoped secret, and publish bounded escaped findings only. |
| Poisoning and misinformation | Diff text can contain instructions or false claims. Use immutable revisions, read-only access, bounded report output, and human verification. A PR can change after the final check, so compare the displayed SHA before relying on findings. |
| Affected people, accessibility, and fairness | Maintainers and contributors benefit from visible findings. Same-repository and size restrictions exclude some PRs, so offer manual review. Public reports can affect contributors or third parties if they repeat identifying details or allegations. |
| Energy and costs | Energy and review usefulness were unmeasured. Time, turn, and estimated spend caps limit exposure. They provide no billing or energy guarantee. |

## Claude independent safety assessment

Claude's final review of [PR #3](https://github.com/Cadams98/verunai-research/pull/3)
at `1622dcc` included a separate read-only assessment by the project's
`safety-reviewer`. The assessment found the Codex review insufficiently
independent and issued the following advisory conclusions.

**Dormant infrastructure:** The founder may merge after personally reviewing
the proposal, provided this independent assessment is recorded and the founder
accepts the remaining shared-identity risk. GitHub cannot distinguish the
founder from an agent using the same identity. In that setup, the agent could
in principle configure the review environment, set the enable variable, or
apply the review label.

**Paid review activation:** Activation remains blocked until a separate
automation identity exists and negative tests show it cannot set the enable
variable, apply the review label, or merge. Record decisions on consent,
provider retention, and public visibility because diffs go to an external
provider and findings appear in a public Actions summary. Complete safe
prompt-injection tests on a non-sensitive fixture covering a diff that
instructs the reviewer to say “LGTM” and a request to read a file outside
the patch. Activation also requires explicit founder approval and verified
environment protection.

Stop and investigate unexpected disclosure, protected-branch bypass, or
execution of proposed code. Revoke exposed credentials and route incidents
privately.
