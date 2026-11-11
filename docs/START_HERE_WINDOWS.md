# Set up Verunai on Windows — founder's first run

**Project:** Verunai (founded by Christian Adams, 2026)  
**Current release:** v0.6.4 research setup and founder attribution, retaining v0.6 experimental neural-v3 ledger  
**What you will run:** Two local Python processes and disposable fictional TEST coins. No paid mining, real cryptocurrency, live AI service, or public network.

## Step 1 — Extract the project

1. Download the Verunai v0.6.4 ZIP and extract it, for example to `C:\Projects\verunai-research`.
2. Open that extracted `verunai-research` folder. Files including `README.md`, `pyproject.toml`, and `SETUP_AND_TEST_WINDOWS.bat` should be visible.
3. Keep the hidden `.claude` folder when moving files. It contains the agent definitions.

## Step 2 — Get the prerequisites

- **Python 3.10 or newer:** https://www.python.org/downloads/windows/ . During installation, enable the option to add Python to PATH if offered. The `py` launcher is supported by our setup script.
- **Git for Windows:** https://git-scm.com/downloads/win . Needed for version history and collaboration.
- Optional: **GitHub Desktop:** https://desktop.github.com/ to publish the repository without remembering Git commands.

Open PowerShell, then check versions (install missing items first):

```powershell
python --version
git --version
```

If `python` is not available but the Python launcher is installed, use `py -3 --version`.

## Step 3 — Install Python dependencies and run the tests

Double-click **`SETUP_AND_TEST_WINDOWS.bat`**. It checks the Python version, installs the project in editable mode (`pip install -e .`), runs project consistency checks, runs automated tests, and executes the two-process ledger demo. It does not install Claude or Codex, connect to GitHub, start a permanent miner, or deploy a public node. Installing Python dependencies does contact the package index if packages are missing.

Alternative in PowerShell (opened inside the extracted folder):

```powershell
python -m pip install -e .
python scripts/check_project_standards.py
python scripts/check_repository_layout.py
python -m unittest discover -s tests -v
python -m verunai demo-ledger-process
```

The demonstration is designed to show a 50-TEST mining reward, a 12-TEST signed transfer with a 1-TEST fee, and final balances of 37 TEST for Alice and 63 TEST for Bob. **TEST has no monetary value.** The CUDA graphics-card-specific test may be skipped unless a supported GPU environment is available.

## Step 4 — Publish to GitHub when you are ready

You need to sign into **your GitHub account**. A public repository is not automatically created by this ZIP.

**Easier option:** Install GitHub Desktop, choose *File → Add local repository* and point to the `verunai-research` folder. If prompted, choose to create a Git repository there. Commit the project. Choose *Publish repository*, name it `verunai-research`, and make it public only after checking for secrets/private files.

**PowerShell alternative:** At https://github.com/new create an **empty** repository named `verunai-research` (do not precreate a README, .gitignore, or license because our project already includes these). Then, from the extracted folder:

```powershell
git init
git branch -M main
git add .
git commit -m "Initial Verunai research release, founded by Christian Adams"
git remote add origin https://github.com/YOUR_USERNAME/verunai-research.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username. If Git asks for your name/email on the first commit, configure them with `git config --global user.name` and `git config --global user.email`. If an existing remote named `origin` already exists, inspect `git remote -v` instead of blindly adding another. Never commit API keys, wallet private keys, `.env` files, or sensitive data.

**After publishing:** Share the GitHub repository URL so we can organize issues and code reviews. No public repository has been created by this release package.

## Step 5 — Start Claude Code with your Claude Pro account

Follow official Windows setup: https://code.claude.com/docs/en/setup . The native Windows installation method may change; use Anthropic's current instructions. After installation, open the project folder in PowerShell and run:

```powershell
claude
```

Choose the **Claude subscription** login if prompted. Project rules are in `CLAUDE.md`, and specialist agents are in `.claude/agents/`. You can also double-click `START_CLAUDE_AGENT_WINDOWS.bat` after installing the CLI.

A safe first task:

> Read CLAUDE.md and AGENTS.md. Review the v0.6 neural mining design as a security auditor. Do not edit code yet. Return a prioritized list of vulnerabilities with reproduction steps and cite exact file paths. Respect the humanity-first safety charter.

## Step 6 — Start Codex with your ChatGPT Plus account

Codex is available through https://chatgpt.com/codex and supported Codex desktop/CLI tools. See https://developers.openai.com/codex/ for current setup options. For cloud coding tasks, connect the GitHub repository after publishing. If you install Codex CLI locally, start it in the project folder with:

```powershell
codex
```

A safe first task:

> Read AGENTS.md, docs/AGENT_BRIEF_V07.md and docs/ENGINEERING_STANDARDS.md. On a new branch, reproduce the neural-v3 mining shortcut concern. Add a measurable baseline-vs-shortcut benchmark, tests, and documentation. Do not change production protocol rules or commit directly to main.

## Step 7 — Keep the agents from colliding

Start with **one agent changing code at a time**. Let the other review results read-only. For concurrent edits, use different Git branches and separate worktrees/clones. Human review is required before merging consensus, safety, or wallet changes. Subscription-based agents have usage limits; they are not background processes simply because their configuration files exist.

## Troubleshooting

- **`python` not recognized:** Install Python, restart PowerShell, or use `py -3`.
- **Missing `cryptography`:** In the project directory run `python -m pip install -e .` again.
- **`claude` or `codex` not recognized:** Install the relevant app/CLI and restart the terminal; the setup script does not install these.
- **Tests skipped:** A CUDA-related test is expected to skip on machines without a configured NVIDIA GPU backend.
- **Git refuses a commit:** Set the Git author name/email; then retry. Using your real name for Git metadata is optional and separate from the public founder credit.
- **Demo fails:** Copy the exact text of the error for troubleshooting; don't paste credentials or private keys.

## Safety reminder

The current project is an experimental local testnet, not a production currency or deployed AI service. Its mining challenge is not yet secure useful-work consensus. Refer to `docs/SECURITY_FINDINGS_V06.md` for known vulnerabilities.
