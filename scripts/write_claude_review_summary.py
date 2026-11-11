"""Render only the Claude action's structured findings in the Actions summary."""

import html
import json
import os
import re
from pathlib import Path


def render_review(payload: str, head_sha: str) -> str:
    """Render bounded plain-text findings for the verified head SHA.

    Args:
        payload: JSON containing only the action's structured review field.
        head_sha: Full commit hash from the trusted workflow event.

    Returns:
        Markdown with the findings escaped inside a plain-text block.

    Raises:
        ValueError: If the revision or review is missing or malformed.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise ValueError("Invalid reviewed commit SHA")
    if len(payload) > 48_000:
        raise ValueError("Structured review exceeds the output limit")
    result = json.loads(payload)
    if not isinstance(result, dict) or set(result) != {"review"}:
        raise ValueError("Expected a single review field")
    review = result["review"]
    if not isinstance(review, str) or not review.strip() or len(review) > 8_000:
        raise ValueError("Expected 1–8,000 characters of review text")
    if any(not (character.isprintable() or character in "\n\r\t") for character in review):
        raise ValueError("Review contains unsupported control characters")
    return (
        f"## Claude review of `{head_sha}`\n\n"
        "Advisory findings. Verify them against the reviewed revision.\n\n"
        f"<pre>{html.escape(review)}</pre>\n"
    )


def main() -> int:
    """Write a safe summary and return a failure status for unusable output."""
    try:
        summary = render_review(os.environ["CLAUDE_REVIEW_JSON"], os.environ["HEAD_SHA"])
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as output:
            output.write(summary)
    except (KeyError, ValueError, OSError):
        print("Claude did not produce a usable structured review. Request a human review.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
