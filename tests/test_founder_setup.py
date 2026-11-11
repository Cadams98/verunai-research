"""Public founder attribution and setup guide checks, not a legal identity proof."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class FounderSetupTests(unittest.TestCase):
    def test_readme_attributes_founder(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Founded by Christian Adams", text)
        self.assertIn("docs/START_HERE_WINDOWS.md", text)

    def test_stewardship_respects_public_interest(self):
        text = (ROOT / "docs/PROJECT_STEWARDSHIP.md").read_text(encoding="utf-8")
        self.assertIn("Christian Adams", text)
        self.assertIn("No founder allocation, premine, sale", text)
        self.assertIn("permissionless", text)

    def test_agents_preserve_founder_and_engineering_rules(self):
        for name in ("AGENTS.md", "CLAUDE.md"):
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn("Christian Adams", text)
                self.assertIn("docs/PROJECT_STEWARDSHIP.md", text)
                self.assertIn("docs/ENGINEERING_STANDARDS.md", text)

    def test_onboarding_keeps_research_limitations(self):
        text = (ROOT / "docs/START_HERE_WINDOWS.md").read_text(encoding="utf-8")
        for phrase in ("TEST has no monetary value", "SECURITY_FINDINGS_V06.md", "GitHub", "Claude Code", "Codex"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertTrue((ROOT / "SETUP_AND_TEST_WINDOWS.bat").is_file())

if __name__ == "__main__":
    unittest.main()
