"""Check the PR handoff validator against completed and blank descriptions."""

import unittest
from pathlib import Path

from scripts.check_pr_description import REQUIRED_SECTIONS, missing_sections


class TestPRDescription(unittest.TestCase):
    """Verify that the checked-in template and required sections agree."""

    def test_completed_description_passes(self):
        body = "\r\n".join(f"## {name}\r\n\r\nDetails for review." for name in REQUIRED_SECTIONS)
        self.assertEqual(missing_sections(body), [])

    def test_unfilled_template_fails(self):
        root = Path(__file__).resolve().parents[1]
        body = (root / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
        self.assertEqual(missing_sections(body), list(REQUIRED_SECTIONS))

    def test_placeholder_and_duplicate_fail(self):
        body = "\n".join(f"## {name}\nA complete section." for name in REQUIRED_SECTIONS)
        body = body.replace("## Testing\nA complete section.", "## Testing\n- [ ] TBD")
        body += "\n## Purpose\nA duplicate section."
        self.assertEqual(missing_sections(body), ["Purpose", "Testing"])
