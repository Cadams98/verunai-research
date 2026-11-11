"""Check that humanity-first policy is discoverable; not an AI safety test."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SafetyPolicyPresenceTests(unittest.TestCase):
    def test_charter_and_test_plan_exist(self):
        for name in ("docs/SAFETY_AND_ETHICS.md", "docs/SAFETY_TEST_PLAN.md"):
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertGreater(len(text), 1000)

    def test_release_gates_are_described(self):
        text = (ROOT / "docs/SAFETY_AND_ETHICS.md").read_text(encoding="utf-8")
        for phrase in ("## Release gates", "Before releasing a trained model", "Stop-ship criteria", "cannot universally enforce"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_agent_entrypoints_reference_charter(self):
        for name in ("AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md"):
            with self.subTest(name=name):
                self.assertIn("docs/SAFETY_AND_ETHICS.md", (ROOT / name).read_text(encoding="utf-8"))

    def test_safety_reviewer_is_read_only(self):
        agent = (ROOT / ".claude/agents/safety-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("tools: Read, Glob, Grep", agent)
        self.assertIn("read-only", agent)


if __name__ == "__main__":
    unittest.main()
