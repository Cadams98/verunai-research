# First Claude Code mission — copy/paste into a Claude Code session opened in this repository

Read `CLAUDE.md`, `AGENTS.md`, `docs/PROTOCOL.md`, and `docs/ROADMAP.md` first. Our goal is a Bitcoin-style competitive block protocol where valid block solutions involve actually useful AI computation. The current implementation is an educational simulator only.

**Mission:** Organize a review using the `consensus-engineer`, `ml-researcher`, and `security-auditor` specialist subagents. Have them independently assess whether the toy candidate protocol can be bypassed without doing the AI work, what can be verified cheaply, and what would be required to train a neural model with GPU miners. Do not change code yet. Create `docs/RESEARCH_REVIEW.md` with a failure-mode table, three candidate next-step protocol designs, and a ranked recommendation. Then ask the owner to approve one design. Include testable falsification experiments and estimated verifier work, not just positive claims. After review, run tests and report the outcome.

Do not launch real tokens, wallets, networks, or spend money. Avoid claims of secure useful-work consensus without proof.
