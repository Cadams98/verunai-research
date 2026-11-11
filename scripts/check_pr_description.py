"""Check that a GitHub pull request includes the required handoff sections."""

import argparse
import json
import re
from pathlib import Path


REQUIRED_SECTIONS = (
    "Purpose", "Implementation", "Testing", "Documentation",
    "Security and safety", "Performance and limitations",
)
SAFETY_FIELDS = (
    "Affected people", "Privacy and consent", "Data and model poisoning",
    "Misinformation", "Accessibility and fairness", "Energy",
    "Independent safety review", "Stop-ship conditions",
)
PLACEHOLDER = re.compile(
    r"(?:tbd|todo|n\W*a|none|placeholder|fill (?:this )?in)(?:[.!?]*|\s*[:—-].*)",
    re.IGNORECASE,
)


def _empty_section(text: str) -> bool:
    for line in text.splitlines():
        content = re.sub(r"^\s*[-*+]\s*(?:\[[ xX]\]\s*)?", "", line).strip()
        if not content.startswith(("#", "```", "~~~")) and re.search(r"\w", content) and not (
            PLACEHOLDER.fullmatch(content) or re.fullmatch(r"<[^<>]+>", content)
        ):
            return False
    return True


def _read_event(path: Path) -> str:
    event = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(event, dict) or not isinstance(event.get("pull_request"), dict):
        raise ValueError("Expected a pull request event object")
    pull_request = event["pull_request"]
    body = pull_request["body"]
    if body is None:
        return ""
    if not isinstance(body, str):
        raise ValueError("Expected a string or null pull request body")
    return body


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
        if name == "Security and safety":
            fields = re.split(r"^###[ \t]+([^\r\n]+)\r?$", matches[0], flags=re.MULTILINE)
            subsections = list(zip(fields[1::2], fields[2::2]))
            for field in SAFETY_FIELDS:
                values = [content for heading, content in subsections if heading.strip() == field]
                if len(values) != 1 or _empty_section(values[0]):
                    missing.append(f"{name} / {field}")
        elif _empty_section(matches[0]):
            missing.append(name)
    return missing


def main() -> int:
    """Validate a GitHub event or Markdown file and return the CLI exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--event", type=Path, help="GitHub pull request event JSON")
    source.add_argument("--body-file", type=Path, help="Local Markdown draft")
    args = parser.parse_args()
    try:
        body = _read_event(args.event) if args.event else args.body_file.read_text(encoding="utf-8-sig")
    except (KeyError, OSError, ValueError):
        print("Cannot read a valid PR description from the specified input.")
        return 1
    missing = missing_sections(body)
    if missing:
        print("Complete these PR sections exactly once: " + ", ".join(missing))
        return 1
    print("Required PR description sections are present. Review claims and evidence separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
