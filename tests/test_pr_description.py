"""Check the PR handoff validator against completed and blank descriptions."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_pr_description import REQUIRED_SECTIONS, SAFETY_FIELDS, missing_sections


ROOT = Path(__file__).resolve().parents[1]


def completed_description() -> str:
    """Build a description with substantive text under every required heading."""
    sections = []
    for name in REQUIRED_SECTIONS:
        sections.extend((f"## {name}", "Details for review."))
        if name == "Security and safety":
            for field in SAFETY_FIELDS:
                sections.extend((f"### {field}", "The review records the expected impact."))
    return "\r\n".join(sections)


class TestPRDescription(unittest.TestCase):
    """Verify that the checked-in template and required sections agree."""

    def test_completed_description_passes(self):
        self.assertEqual(missing_sections(completed_description()), [])

    def test_unfilled_template_fails(self):
        body = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
        self.assertIn("Purpose", missing_sections(body))
        for field in SAFETY_FIELDS:
            self.assertIn(f"Security and safety / {field}", missing_sections(body))

    def test_placeholder_and_duplicate_fail(self):
        body = completed_description().replace("\r\n", "\n")
        body = body.replace("## Testing\nDetails for review.", "## Testing\n- [ ] TBD\n- <result>")
        body += "\n## Purpose\nA duplicate section."
        self.assertEqual(missing_sections(body), ["Purpose", "Testing"])

    def test_missing_file_and_malformed_event_fail_without_traceback(self):
        checker = ROOT / "scripts" / "check_pr_description.py"
        with tempfile.TemporaryDirectory() as directory:
            event = Path(directory) / "event.json"
            for content in (None, "{", "[]", '{"pull_request":{}}',
                            '{"pull_request":{"body":17}}', '{"pull_request":{"body":null}}'):
                if content is not None:
                    event.write_text(content, encoding="utf-8")
                with self.subTest(content=content):
                    result = subprocess.run(
                        [sys.executable, "-B", str(checker), "--event", str(event)],
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertNotIn("Traceback", result.stderr)

    def test_missing_base_checker_only_passes_for_pr_three_bootstrap(self):
        git = shutil.which("git")
        bash = Path(git).resolve().parents[1] / "bin" / "bash.exe" if os.name == "nt" and git else None
        bash = str(bash) if bash and bash.is_file() else shutil.which("bash")
        if not bash:
            self.skipTest("Bash is required to exercise the workflow step")
        workflow = (ROOT / ".github" / "workflows" / "pr-handoff.yml").read_text(encoding="utf-8")
        run_script = "\n".join(line[10:] for line in workflow.split("        run: |\n", 1)[1].splitlines())
        bootstrap = "6236f5d27d2fbc70a7a850b0a85486c8173164fc"
        cases = (("3", bootstrap, 0), ("4", bootstrap, 1), ("3", "f" * 40, 1))
        with tempfile.TemporaryDirectory() as directory:
            for number, base, status in cases:
                env = {**os.environ, "GITHUB_REPOSITORY": "Cadams98/verunai-research",
                       "PR_NUMBER": number, "BASE_SHA": base}
                with self.subTest(pr=number, base=base):
                    result = subprocess.run(
                        [bash, "-c", run_script], cwd=directory, env=env,
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, status, result.stderr)
