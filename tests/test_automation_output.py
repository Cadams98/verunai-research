"""Exercise draft publication guards and the hosted review output boundary."""

import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import publish_codex_draft as publisher
from scripts.write_claude_review_summary import render_review


class TestAutomationOutput(unittest.TestCase):
    """Verify the scope of publication and the rendering of untrusted findings."""

    def test_review_is_escaped_and_labeled_with_the_exact_sha(self):
        sha = "a" * 40
        output = render_review(json.dumps({"review": "</pre><img src=x>"}), sha)
        self.assertIn(sha, output)
        self.assertIn("&lt;img src=x&gt;", output)
        self.assertNotIn("<img", output)
        for payload in ("{", '{"review":""}', '{"review":42}', '{"review":"ok","raw":"no"}'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                render_review(payload, sha)

    def test_publisher_refuses_main_and_unexpected_origins(self):
        with self.assertRaisesRegex(ValueError, "dedicated"):
            publisher._validate_checkout("main")
        with patch.object(publisher, "git_output", return_value="https://example.invalid/repo"):
            with self.assertRaisesRegex(ValueError, "origin push URL"):
                publisher._validate_checkout("codex/task")

    def test_failed_push_cannot_proceed_to_pr_creation(self):
        with patch.object(publisher.subprocess, "run", side_effect=subprocess.TimeoutExpired("git", 90)) as run:
            result = publisher._publish("codex/task", "Title", Path("body.md"), "https://example.invalid")
        self.assertEqual(result, 1)
        run.assert_called_once()
        self.assertIn("HEAD:refs/heads/codex/task", run.call_args.args[0])

    def test_failed_pr_creation_reports_the_comparison_url(self):
        url = "https://github.com/Cadams98/verunai-research/compare/main...codex/task?expand=1"
        with patch.object(publisher.subprocess, "run", side_effect=[None, FileNotFoundError]) as run:
            with patch("builtins.print") as output:
                result = publisher._publish("codex/task", "Title", Path("body.md"), url)
        self.assertEqual(result, 1)
        self.assertIn("--draft", run.call_args.args[0])
        self.assertIn(url, output.call_args.args[0])
