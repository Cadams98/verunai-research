"""Publish the current committed Codex branch as a draft VERUNAI PR."""

import argparse
import re
import subprocess
from pathlib import Path

if __package__:
    from .check_pr_description import missing_sections
else:
    from check_pr_description import missing_sections


REPOSITORY = "Cadams98/verunai-research"
ORIGIN_URLS = {
    f"https://github.com/{REPOSITORY}.git",
    f"https://github.com/{REPOSITORY}",
    f"git@github.com:{REPOSITORY}.git",
}


def git_output(*args: str) -> str:
    """Run a Git query and return its trimmed output, or a user-facing error."""
    try:
        return subprocess.check_output(["git", *args], text=True, timeout=30).strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError(f"Git query failed ({args[0]}). Check Git and the local checkout.") from error


def main() -> int:
    """Validate the publication inputs, then optionally push and open a draft."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--publish", action="store_true", help="Push and open the draft")
    args = parser.parse_args()
    try:
        branch = git_output("branch", "--show-current")
        _validate_checkout(branch)
    except ValueError as error:
        parser.error(str(error))
    if not args.title.strip():
        parser.error("Provide a descriptive PR title")
    try:
        body = args.body_file.read_text(encoding="utf-8-sig")
    except (OSError, ValueError):
        parser.error("Cannot read the PR body file as UTF-8")
    missing = missing_sections(body)
    if missing:
        parser.error("Complete the PR sections: " + ", ".join(missing))
    url = f"https://github.com/{REPOSITORY}/compare/main...{branch}?expand=1"
    if not args.publish:
        print(f"Dry run passed for {branch}. Draft comparison: {url}")
        return 0
    return _publish(branch, args.title, args.body_file, url)


def _validate_checkout(branch: str) -> None:
    if not re.fullmatch(r"codex/[a-z0-9][a-z0-9-]*", branch):
        raise ValueError("Use a dedicated codex/<task> branch")
    origins = git_output("remote", "get-url", "--push", "--all", "origin").splitlines()
    if len(origins) != 1 or origins[0] not in ORIGIN_URLS:
        raise ValueError("Expected one origin push URL for the VERUNAI GitHub repository")
    if git_output("status", "--porcelain"):
        raise ValueError("Commit the authorized changes in a clean, dedicated checkout first")
    if not git_output("rev-list", "origin/main..HEAD", "--max-count=1"):
        raise ValueError("The branch has no commit to propose against origin/main")


def _publish(branch: str, title: str, body_file: Path, url: str) -> int:
    try:
        subprocess.run(
            ["git", "push", "--set-upstream", "origin", f"HEAD:refs/heads/{branch}"],
            check=True,
            timeout=90,
        )
    except (OSError, subprocess.SubprocessError):
        print("Push did not complete successfully. Check Git authentication and the remote branch before retrying.")
        return 1
    try:
        subprocess.run(
            ["gh", "pr", "create", "--repo", REPOSITORY, "--draft", "--base", "main",
             "--head", branch, "--title", title, "--body-file", str(body_file)],
            check=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        print(f"Branch published, but draft creation was not confirmed. Check gh auth status "
              f"and existing PRs, or open a draft at {url}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
