import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tlinter.cli import main
from tlinter.model import load

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(argv)
        return code, out.getvalue()

    def test_clean_transcript_exits_zero(self):
        code, out = self.run_cli(["lint", str(ROOT / "samples" / "clean.json")])
        self.assertEqual(code, 0)
        self.assertIn("clean", out)

    def test_messy_transcript_exits_one(self):
        code, out = self.run_cli(["lint", str(ROOT / "samples" / "messy.json")])
        self.assertEqual(code, 1)
        self.assertIn("unverified_claim", out)
        self.assertIn("destructive_command", out)

    def test_json_output_is_parseable(self):
        code, out = self.run_cli(["lint", "--json", str(ROOT / "samples" / "messy.json")])
        payload = json.loads(out)
        self.assertEqual(payload["transcript"], str(ROOT / "samples" / "messy.json"))
        self.assertTrue(any(f["rule"] == "scope_creep" for f in payload["findings"]))

    def test_samples_parse(self):
        for name in ("clean.json", "messy.json"):
            with self.subTest(sample=name):
                self.assertTrue(load(ROOT / "samples" / name).steps)

    def test_invalid_file_exits_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            code, _ = self.run_cli(["lint", str(bad)])
            self.assertEqual(code, 3)

    def test_rules_command_lists_all(self):
        code, out = self.run_cli(["rules"])
        self.assertEqual(code, 0)
        self.assertIn("unverified_claim", out)
        self.assertEqual(len(out.strip().splitlines()), 7)
