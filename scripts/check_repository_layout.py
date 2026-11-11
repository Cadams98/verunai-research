"""Validate Verunai's basic folder hygiene without changing any files.

This checks layout conventions, not module design or consensus correctness.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRECTORIES = (
    "verunai", "tests", "docs", "docs/decisions", "docs/milestones",
    "evidence", "examples", "scripts", ".github/workflows", ".claude/agents",
)
REQUIRED_FILES = (
    "docs/FOLDER_STRUCTURE.md", "docs/ARCHITECTURE.md",
    "docs/SAFETY_AND_ETHICS.md", "docs/SAFETY_TEST_PLAN.md",
    "docs/START_HERE_WINDOWS.md", "docs/PROJECT_STEWARDSHIP.md",
    "docs/decisions/0002-repository-layout.md", "examples/README.md",
    "pyproject.toml", "README.md", "AGENTS.md", "CLAUDE.md",
)


def check_layout(root: Path) -> list[str]:
    """Return human-readable repository structure errors, without side effects."""
    issues: list[str] = []
    for relative in REQUIRED_DIRECTORIES:
        if not (root / relative).is_dir():
            issues.append(f"Required directory missing: {relative}")
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            issues.append(f"Required file missing: {relative}")

    expected_root_markdown = {"README.md", "AGENTS.md", "CLAUDE.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md"}
    for item in root.iterdir():
        if item.is_file():
            if item.suffix.lower() == ".md" and item.name not in expected_root_markdown:
                issues.append(f"Unexpected root Markdown file; move it under docs/: {item.name}")
            if item.name.startswith("MILESTONE_") and item.suffix == ".md":
                issues.append(f"Move historical report under docs/milestones/: {item.name}")
            if item.suffix.lower() in {".json", ".pyc"} and item.name != "RELEASE_SHA256_MANIFEST.json":
                issues.append(f"Generated data should not be in repository root: {item.name}")
            if item.suffix == ".py":
                issues.append(f"Python code belongs in verunai/ or scripts/, not root: {item.name}")

    # Check for tracked build artifacts in source distributions. Local ignored
    # __pycache__ created during test runs should not fail this check.
    return issues


def main() -> int:
    issues = check_layout(ROOT)
    if issues:
        for issue in issues:
            print("ERROR:", issue)
        return 1
    print("Repository layout conventions verified; architecture still needs human review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
