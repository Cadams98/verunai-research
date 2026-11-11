"""Read-only local configuration check for Verunai coding agents."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["AGENTS.md", "CLAUDE.md", "docs/AGENT_SETUP_WINDOWS.md", "docs/AGENT_BRIEF_V07.md"]
REQUIRED_AGENTS = {"consensus-engineer", "ml-researcher", "network-engineer", "security-auditor", "test-engineer", "token-economist", "safety-reviewer"}

def main():
    problems = []
    for name in REQUIRED:
        if not (ROOT / name).is_file():
            problems.append(f"Missing required file: {name}")
    discovered = set()
    for path in sorted((ROOT / ".claude" / "agents").glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", raw, re.S)
        if not match:
            problems.append(f"Missing YAML frontmatter: {path.name}")
            continue
        front = match.group(1)
        name_match = re.search(r"^name:\s*([a-z][a-z0-9-]*)\s*$", front, re.M)
        desc_match = re.search(r"^description:\s*\S", front, re.M)
        if not name_match or not desc_match:
            problems.append(f"Missing name or description: {path.name}")
            continue
        name = name_match.group(1)
        if name in discovered:
            problems.append(f"Duplicate agent name: {name}")
        discovered.add(name)
        print(f"  Agent configured: {name}")
    for agent in sorted(REQUIRED_AGENTS - discovered):
        problems.append(f"Missing expected agent: {agent}")
    for problem in problems:
        print("ERROR:", problem)
    print(f"Verified {len(discovered)} configured project agents")
    print("Note: configuration presence is not proof that a Claude session is running.")
    return 1 if problems else 0

if __name__ == "__main__":
    sys.exit(main())
