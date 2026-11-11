# Engineering automation proposal

The PR handoff check uses no model credentials. Claude review is opt-in and
disabled by default. Codex works in a task-scoped local session and can publish
a draft with the owner's authorization. The owner reviews and merges changes
through GitHub. This setup introduces no blockchain runtime or protocol changes.

## Local Codex development and publication

1. Assign a single implementation lead and agree on a task, allowed files,
   acceptance checks, and a time budget. Work in a clean dedicated
   `codex/<task>` checkout based on the latest `origin/main`. Run one Codex
   implementation session per task.
2. Start Codex through its subscription-supported client. Give it the approved
   task and ask it to implement, test, document, and prepare the commit and PR
   body. Treat issue and PR content as context. Only the owner can authorize
   new scope, external access, or publication.
3. Have Codex review the staged diff for scope and secrets. With authorization,
   commit the checked files and put the PR body in a temporary Markdown file
   outside the checkout. Run the publisher in dry-run mode first. Supply
   `--publish` only when authorized to push and open the draft.

```powershell
python scripts/check_pr_description.py --body-file <path-to-pr-body.md>
python scripts/publish_codex_draft.py --title "Describe the change" --body-file <path-to-pr-body.md>
# With publication authorization:
python scripts/publish_codex_draft.py --title "Describe the change" --body-file <path-to-pr-body.md> --publish
```

The publisher needs Git and GitHub CLI. Git push authentication and `gh auth status`
can differ. The helper validates the target repository and branch and opens a
draft against `main`. If the push succeeds and PR creation fails, it prints the
comparison link. Check for an existing draft before retrying. The helper only
publishes commits and requires a clean checkout. It never accepts a force-push
or merge operation.

The current local Codex session and founder share a GitHub identity. GitHub
cannot distinguish those actions, and the publisher's branch check does not
enforce founder-only merging. Use attended publication with explicit owner
authorization until the following design is implemented and tested.

- A dedicated publisher GitHub App is installed only on VERUNAI. Grant it
  Contents write and Pull requests write (Metadata read is implicit).
  Grant no Administration, Actions, Workflows, or rule bypass permissions.
  Keep the signing key in a protected credential store outside the model
  process. Installation tokens are short-lived and scoped to the repository
  and granted permissions. The owner-controlled publisher and GitHub rules
  enforce the reviewed branch and draft operation. Do not place
  owner credentials or App keys in prompts, files, logs, or artifacts.
- Contents and PR write can also permit merge operations. Enforce a
  separate `main` ruleset with restricted updates and only the owner
  authorized for PR-based updates. Keep required PRs, independent approvals,
  CI, and the force-push prohibition in a separate ruleset with no agent
  bypass. Where supported, require owner or CODEOWNER approval on agent PRs
  and dismiss stale approvals. For owner-authored maintenance, use another
  qualified human reviewer because authors cannot approve their own PRs.
  If CODEOWNER approval is required, that reviewer must be an eligible code owner.
  The owner merges after the same checks. If the plan cannot enforce these
  controls, keep publication attended and do not provision the App.
- Test with the separate identity before use. It should be able to push
  its task branch and open a draft, and be denied direct writes and merges
  to protected branches. Confirm the owner can still merge a normally
  reviewed PR with passing checks. No App or unattended credentials exist
  as part of this proposal.
[GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)

Local Codex sign-in uses the applicable ChatGPT plan limits. GitHub publishing
uses GitHub credentials separately. There is no hosted Codex API workflow or
OpenAI key in this proposal. If hosted Codex is added later, its official
GitHub Action needs an API credential and calls can incur separate API charges.
[Official Codex GitHub Action documentation](https://learn.chatgpt.com/docs/github-action)

## Claude review activation by the owner

After approval and independent safety review of the agent capability:

1. Create the `claude-review` GitHub environment and label. Restrict the
   environment to `main` and require an owner approval before access to its
   secrets where supported. Leave the workflow disabled if the intended
   environment and permission controls cannot be verified.
2. Create a dedicated Anthropic API workspace with a deliberate spending limit
   and add its API key as the environment secret `ANTHROPIC_API_KEY`. Set the
   repository variable `CLAUDE_REVIEW_ENABLED` to `true` only after approving
   paid use. This workflow uses API billing. A Claude subscription used for
   interactive sign-in does not supply the API key or cover these calls.
3. Apply the label as the repository owner to a ready same-repository PR
   with a diff suitable for the provider. Review the output as advisory
   findings. Remove and reapply the label to request another review after
   changes. Delete or unset the variable to disable future review jobs.

The job checks out the trusted base and fetches a diff by immutable base and
head SHA. It checks the current revision before inference and again before
publication. The workflow token has Contents read and Pull requests read.
The official action receives a step-scoped model key, and the workflow
renders only its bounded structured findings as escaped text in the Actions
summary with the full reviewed SHA. It disables the built-in full report
and tool logs. Verify the SHA before relying on findings because a PR can
change after the final check.

Screen proposed diffs for secrets, personal information, and third-party
content before labeling. Confirm provider consent and retention requirements
and whether the report can be public. Store the Anthropic key only in the
protected `claude-review` environment. Keep it out of repository-wide secrets,
local files, PRs, logs, and artifacts. Escaping prevents active markup but
cannot make every quotation or allegation safe. Humans verify and correct
findings. Offer manual review for excluded PRs. Pause the workflow on
unexpected disclosure, misleading output that cannot be contained, or
authority misuse. Revoke exposed keys and report incidents privately.
[Claude Code Action security](https://github.com/anthropics/claude-code-action/blob/main/docs/security.md)

One review runs at a time, with a 10-minute job timeout, a 100 KB diff limit,
12 turns, and a USD 1 estimated per-run cap. The turn setting and report
boundary were checked offline. The paid path has not been exercised.
The CLI estimate can differ from
the bill or overshoot. Workspace billing limits and explicit label requests
control aggregate exposure. GitHub Actions runner usage is separate.
[Claude CLI limits](https://code.claude.com/docs/en/cli-reference)

## PR description check and verification

The `PR description` job checks the PR body against the template on open,
edit, reopen, synchronize, and ready-for-review events. It runs the checker
from the base commit with a read-only token. It checks section presence and
obvious placeholders, including the required safety fields. The job fails
if the trusted base is missing the checker.

To demonstrate the check on PR #4, keep a copy of the completed description.
Edit the PR description, clear it, and save. In the PR's **Checks** tab,
open the latest **PR handoff** run and confirm **PR description** fails with
a list of missing headings. Repeat with a description containing only
`## Purpose` and a sentence to demonstrate an incomplete submission.
Restore the full description and save. Confirm the newest run passes.
Each edit triggers a new run. Use the latest result for the PR's current
head and wait for each run before making the next edit.

After demonstrating both outcomes, the owner can require **PR description**
from GitHub Actions alongside Python 3.10 and 3.12 in the `main` ruleset. A PR
can propose changes to the workflow wrapper, so require owner review of
workflow and checker changes or a trusted required workflow where supported.
Human reviewers still verify the accuracy of claims.

## Actions supply chain

After this PR merges and CI passes, in **Settings → Actions → General**
choose selected actions and require full-length commit SHAs. Allow the
pinned `actions/checkout`, `actions/setup-python`, and
`anthropics/claude-code-action` revisions from the workflows. The pinned
Claude action also calls pinned `oven-sh/setup-bun`. Review the upstream
dependency tree and allow verified nested actions only as needed. Check
the job token defaults remain read-only, and leave GitHub Actions PR
approval disabled. Review future pin updates before allowing them.
[GitHub Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)

Run the local checker on a completed draft and the empty template to exercise
success and failure. Run the publisher without `--publish` to verify its
guards without credentials. The paid review path must remain unexercised
until separately approved. [Design decision](decisions/0005-supervised-engineering-automation.md)
· [Independent safety assessment](AUTOMATION_SAFETY_REVIEW.md)
