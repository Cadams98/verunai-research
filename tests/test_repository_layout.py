"""Regression tests for Verunai repository layout conventions."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_repository_layout import check_layout  # noqa: E402


class RepositoryLayoutTests(unittest.TestCase):
    def test_current_repository_passes(self):
        self.assertEqual(check_layout(ROOT), [])

    def test_missing_directories_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            issues = check_layout(Path(directory))
            self.assertTrue(any("Required directory missing" in issue for issue in issues))

    def test_old_report_in_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MILESTONE_V99_REPORT.md"
            path.write_text("Old report", encoding="utf-8")
            self.assertTrue(any("historical report" in issue for issue in check_layout(Path(directory))))

    def test_generated_json_in_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "test-output.json").write_text("{}", encoding="utf-8")
            self.assertTrue(any("Generated data" in issue for issue in check_layout(Path(directory))))

    def test_miscellaneous_document_in_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "DESIGN_NOTES.md").write_text("Notes", encoding="utf-8")
            self.assertTrue(any("Unexpected root Markdown" in issue for issue in check_layout(Path(directory))))

    def test_python_module_in_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "misc.py").write_text("pass", encoding="utf-8")
            self.assertTrue(any("Python code" in issue for issue in check_layout(Path(directory))))


if __name__ == "__main__":
    unittest.main()
