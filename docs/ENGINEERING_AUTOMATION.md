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

Use an implementation identity with repository write access and no admin or
ruleset bypass privileges. Required checks and PRs alone do not make merges
owner-only. Before unattended credentials are introduced, verify server-side
restrictions using a separate owner-only update rule or equivalent GitHub
control supported by the plan. Keep PR and CI rules in force for the owner.
Keep workflow identities off bypass lists and review any changes to workflows,
permissions, and repository rules. The local helper is a scope guard, and the
GitHub rules are the authorization boundary.
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

The job checks out only the trusted base and passes the PR diff as data. It
uses GitHub's job token with repository contents read and PR comments write.
No GitHub App installation token, personal GitHub token, OIDC permission, or
checkout credentials are passed to the reviewer. Model tools are limited to
reading and posting findings. PR metadata and diffs can contain misleading
instructions, private information, or secrets. Review only changes suitable
for the provider and treat output as untrusted until checked by a human.
[Claude Code Action security](https://github.com/anthropics/claude-code-action/blob/main/docs/security.md)

One review runs at a time, with a 10-minute job timeout, a 100 KB diff limit,
six turns, and a USD 1 estimated per-run cap. The CLI estimate can differ from
the bill or overshoot. Workspace billing limits and explicit label requests
control aggregate exposure. GitHub Actions runner usage is separate.
[Claude CLI limits](https://code.claude.com/docs/en/cli-reference)

## PR description check and verification

The `PR description` job checks the PR body against the template on open,
edit, reopen, synchronize, and ready-for-review events. It runs the checker
from the base commit with a read-only token. It checks section presence and
obvious placeholders. If the base predates the checker, the job reports
that validation was skipped and the description needs manual review.
Human review verifies accuracy. After a test PR proves
the check appears and updates as expected, the owner can require it alongside
Python 3.10 and 3.12. Review changes to the check itself as infrastructure
changes.

Run the local checker on a completed draft and the empty template to exercise
success and failure. Run the publisher without `--publish` to verify its
guards without credentials. The paid review path must remain unexercised
until separately approved. [Design decision](decisions/0005-supervised-engineering-automation.md)
