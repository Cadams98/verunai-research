# Verunai Windows AI-agent setup (Codex + Claude Code)

**Founder:** Christian Adams (2026). **New users should begin with [`START_HERE_WINDOWS.md`](START_HERE_WINDOWS.md)** and `SETUP_AND_TEST_WINDOWS.bat`.

The existing ChatGPT Plus and Claude Pro subscriptions are enough to start with subscription-authenticated Codex and Claude Code, within their respective usage limits. No model API key is needed when you sign into their subscription-supported clients. API calls made from *your Verunai software* are different and may be billed separately; do not enable them by default.

## 1. Prepare the project

1. Download/extract the Verunai **latest Verunai** ZIP somewhere convenient, e.g. `C:\Projects\verunai-research`. Keep the `.claude` hidden folder when extracting; it contains the actual Claude subagent definitions.
2. Install Python 3.10+ from python.org if necessary, and Git for Windows (https://git-scm.com/downloads/win) if not installed.
3. In the extracted directory, double-click `CHECK_AGENT_SETUP_WINDOWS.bat` to check tools. This check does not install anything or use the network.
4. Open PowerShell in the project folder and run:

   ```powershell
   python -m pip install -e .
   python -m unittest discover -s tests -v
   python -m verunai demo-ledger-process
   ```

## 2. Sign in to Claude Code (Claude Pro)

Preferred Windows installer documented by Anthropic:

```powershell
winget install Anthropic.ClaudeCode
```

Close/reopen PowerShell, change into the extracted `verunai-research` directory, and run `claude`. Sign in with the Claude account associated with Pro, not an API-billing account. `START_CLAUDE_AGENT_WINDOWS.bat` also opens Claude Code from that directory after installation.

Try this first prompt:

> Read CLAUDE.md and AGENTS.md. List the seven project subagents from .claude/agents and their responsibilities. Ask the security-auditor and consensus-engineer to independently assess the v0.6 proof-of-useful-work security weakness. Return a concise prioritized report with specific tests; do not modify consensus code or claim a secure blockchain.

Claude Code's project-specific agents live under `.claude/agents/` and are only active when Claude Code is launched/used. They do not run indefinitely by themselves.

## 3. Sign in to Codex (ChatGPT Plus)

Open https://chatgpt.com/codex or the Codex feature of the ChatGPT desktop app; sign in with your ChatGPT Plus account. If using the CLI instead, install it according to the current official Codex CLI documentation and run `codex` inside this project directory; `START_CODEX_AGENT_WINDOWS.bat` is only for CLI users with Codex already installed.

For Codex Cloud: first publish the repo to GitHub and connect it in Codex, then select the repo and give Codex a task. Local Codex can work in the extracted directory without publishing first.

First Codex task:

> Read AGENTS.md and docs/AGENT_BRIEF_V07.md. Work on a new codex/shortcut-benchmark branch. Implement a reproducible baseline-versus-attacker-optimized valid block-candidate benchmark for the existing neural-v3 test protocol; do not rewrite protocol rules. Add tests demonstrating that independent validators accept both candidate strategies. Report performance, correctness, and the limits of current proof-of-useful-work security. Do not modify mainnet or token economics.

## 4. Protect changes with Git and separate branches

Inside the project folder, initialize local version control if it is not already a Git repository:

```powershell
git init
git add .
git commit -m "Import Verunai v0.6 agent-team baseline"
```

You may need to configure your Git name and email if it's your first commit. Create a **public GitHub repository** using https://github.com/new when ready. Do not upload wallet keys, .env files, tokens, or personal information. Then push the reviewed baseline using GitHub's instructions.

Give Codex and Claude *different branches* and preferably separate worktrees (or separate cloned directories) so they cannot overwrite one another. Never let both write to the same working tree simultaneously. Make human approval mandatory for merging protocol changes.

## 5. Review and handoff

- First run: Codex implements shortcut benchmark, Claude audits, project owner reviews both results.
- Copy Claude's findings into a GitHub issue; link Codex's branch or pull request.
- Run all tests again before accepting changes.
- Record run commands, operating system, hardware, pass/fail, and known limitations.

## Important limits

Subscriptions are not free access to unlimited API automation. No always-on Verunai agent has been deployed by this package. This is a set of useful configurations and launch helpers. Your computer, account sign-ins, branch permissions, and usage limits still govern what happens.
