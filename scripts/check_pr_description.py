"""Check that a GitHub pull request includes the required handoff sections."""

import argparse
import json
import re
from pathlib import Path


REQUIRED_SECTIONS = (
    "Purpose", "Implementation", "Testing", "Documentation",
    "Security and safety", "Performance and limitations",
)


def missing_sections(body: str) -> list[str]:
    """Return required level-two headings with missing or placeholder content.

    Args:
        body: Markdown text from the pull request description.

    Returns:
        Required section names that occur other than once or lack content.
    """
    visible = re.sub(r"<!--.*?(?:-->|\Z)", "", body, flags=re.DOTALL)
    parts = re.split(r"^##[ \t]+([^\r\n]+)\r?$", visible, flags=re.MULTILINE)
    sections = list(zip(parts[1::2], parts[2::2]))
    missing = []
    for name in REQUIRED_SECTIONS:
        matches = [content for heading, content in sections if heading.strip() == name]
        if len(matches) != 1:
            missing.append(name)
            continue
        words = re.findall(r"\w+", matches[0].casefold())
        if not words or " ".join(words) in {"tbd", "todo", "n a", "none", "placeholder"}:
            missing.append(name)
    return missing


def main() -> int:
    """Validate a GitHub event or Markdown file and return the CLI exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--event", type=Path, help="GitHub pull request event JSON")
    source.add_argument("--body-file", type=Path, help="Local Markdown draft")
    args = parser.parse_args()
    if args.event:
        event = json.loads(args.event.read_text(encoding="utf-8"))
        body = event["pull_request"]["body"] or ""
    else:
        body = args.body_file.read_text(encoding="utf-8-sig")
    missing = missing_sections(body)
    if missing:
        print("Complete these PR sections exactly once: " + ", ".join(missing))
        return 1
    print("Required PR description sections are present. Review claims and evidence separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
