"""Publish the current committed Codex branch as a draft VERUNAI PR."""

import argparse
import re
import subprocess
from pathlib import Path

from check_pr_description import missing_sections


REPOSITORY = "Cadams98/verunai-research"
ORIGIN_URLS = {
    f"https://github.com/{REPOSITORY}.git",
    f"https://github.com/{REPOSITORY}",
    f"git@github.com:{REPOSITORY}.git",
}


def git_output(*args: str) -> str:
    """Run a Git query with the given arguments and return its trimmed output."""
    return subprocess.check_output(["git", *args], text=True, timeout=30).strip()


def main() -> int:
    """Validate the publication inputs, then optionally push and open a draft."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--publish", action="store_true", help="Push and open the draft")
    args = parser.parse_args()
    branch = git_output("branch", "--show-current")
    if not re.fullmatch(r"codex/[a-z0-9][a-z0-9-]*", branch):
        parser.error("Use a dedicated codex/<task> branch")
    origins = git_output("remote", "get-url", "--push", "--all", "origin").splitlines()
    if len(origins) != 1 or origins[0] not in ORIGIN_URLS:
        parser.error("Expected one origin push URL for the VERUNAI GitHub repository")
    if git_output("status", "--porcelain"):
        parser.error("Commit the authorized changes in a clean, dedicated checkout first")
    if not git_output("rev-list", "origin/main..HEAD", "--max-count=1"):
        parser.error("The branch has no commit to propose against origin/main")
    if not args.title.strip():
        parser.error("Provide a descriptive PR title")
    missing = missing_sections(args.body_file.read_text(encoding="utf-8-sig"))
    if missing:
        parser.error("Complete the PR sections: " + ", ".join(missing))
    url = f"https://github.com/{REPOSITORY}/compare/main...{branch}?expand=1"
    if not args.publish:
        print(f"Dry run passed for {branch}. Draft comparison: {url}")
        return 0

    subprocess.run(
        ["git", "push", "--set-upstream", "origin", f"HEAD:refs/heads/{branch}"],
        check=True,
        timeout=90,
    )
    try:
        subprocess.run(
            ["gh", "pr", "create", "--repo", REPOSITORY, "--draft", "--base", "main",
             "--head", branch, "--title", args.title, "--body-file", str(args.body_file)],
            check=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        print(f"Branch published. Check for an existing draft or open one at {url}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
