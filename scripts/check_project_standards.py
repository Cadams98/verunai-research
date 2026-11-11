"""Read-only check that engineering policy and review entrypoints exist.

This does not prove code readability or documentation correctness: human review
remains necessary. Uses only the Python standard library.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "docs/SAFETY_AND_ETHICS.md",
    "docs/PROJECT_STEWARDSHIP.md",
    "docs/START_HERE_WINDOWS.md",
    "docs/decisions/0004-founder-credit-and-community-stewardship.md",
    "docs/SAFETY_TEST_PLAN.md",
    "docs/decisions/0003-humanity-first-safety.md",
    ".claude/agents/safety-reviewer.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "docs/ENGINEERING_STANDARDS.md",
    "docs/ARCHITECTURE.md",
    "docs/FOLDER_STRUCTURE.md",
    "docs/decisions/0002-repository-layout.md",
    "docs/decisions/0001-readable-modular-documented.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
)


def main() -> int:
    problems = []
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file():
            problems.append(f"Missing policy file: {relative}")
        elif len(path.read_text(encoding="utf-8").strip()) < 80:
            problems.append(f"Empty or suspiciously short policy file: {relative}")
    for relative in ("AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md"):
        path = ROOT / relative
        if path.is_file() and "docs/ENGINEERING_STANDARDS.md" not in path.read_text(encoding="utf-8"):
            problems.append(f"Missing engineering standards reference: {relative}")
    for relative in ("AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", ".github/PULL_REQUEST_TEMPLATE.md"):
        path = ROOT / relative
        if path.is_file() and "docs/SAFETY_AND_ETHICS.md" not in path.read_text(encoding="utf-8"):
            problems.append(f"Missing safety charter reference: {relative}")
    for filename in sorted((ROOT / ".claude" / "agents").glob("*.md")):
        if "docs/ENGINEERING_STANDARDS.md" not in filename.read_text(encoding="utf-8"):
            problems.append(f"Missing engineering standards reference: {filename.relative_to(ROOT)}")
    for filename in sorted((ROOT / ".claude" / "agents").glob("*.md")):
        if "docs/SAFETY_AND_ETHICS.md" not in filename.read_text(encoding="utf-8"):
            problems.append(f"Missing safety charter reference: {filename.relative_to(ROOT)}")
    for error in problems:
        print("ERROR:", error)
    if problems:
        return 1
    print(f"Repository standards entrypoints verified ({len(REQUIRED)} required files).")
    print("Human review still required for readability, documentation and scalability.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
