import unittest

from tlinter.model import parse_transcript
from tlinter.rules import (
    destructive_command,
    ignored_failure,
    is_verification,
    lint,
    no_verification,
    retry_storm,
    risky_change_unflagged,
    scope_creep,
    unverified_claim,
)


def transcript(*steps, task="Fix the parser in src/parser.py"):
    return parse_transcript({"task": task, "steps": list(steps)})


def tool(command, ok=True, **kw):
    return {"kind": "tool", "tool": "bash", "command": command, "ok": ok, **kw}


def text(body):
    return {"kind": "text", "text": body}


def edit(path):
    return {"kind": "edit", "path": path}


class RuleTests(unittest.TestCase):
    def test_unverified_claim_fires_without_prior_verification(self):
        t = transcript(edit("src/parser.py"), text("All tests pass."))
        self.assertEqual([f.rule for f in unverified_claim(t)], ["unverified_claim"])

    def test_unverified_claim_silent_when_verification_passed(self):
        t = transcript(edit("src/parser.py"), tool("python -m unittest", ok=True),
                       text("All tests pass."))
        self.assertEqual(unverified_claim(t), [])

    def test_unverified_claim_ignores_failed_verification(self):
        t = transcript(tool("pytest", ok=False), text("Tests are green."))
        self.assertEqual(len(unverified_claim(t)), 1)

    def test_ignored_failure_fires_when_never_rerun(self):
        t = transcript(tool("pytest", ok=False), text("Done."))
        self.assertEqual([f.rule for f in ignored_failure(t)], ["ignored_failure"])

    def test_ignored_failure_clears_after_green_rerun(self):
        t = transcript(tool("pytest", ok=False), tool("pytest", ok=True))
        self.assertEqual(ignored_failure(t), [])

    def test_destructive_commands(self):
        for command in ["rm -rf build", "git push --force origin main",
                        "psql -c 'DROP TABLE users'", "chmod 777 .", "sudo apt install x"]:
            with self.subTest(command=command):
                self.assertTrue(destructive_command(transcript(tool(command))))

    def test_safe_commands_pass(self):
        for command in ["pytest -q", "python -m unittest", "git status", "ls -la"]:
            with self.subTest(command=command):
                self.assertEqual(destructive_command(transcript(tool(command))), [])

    def test_no_verification_warns(self):
        t = transcript(edit("src/parser.py"), text("Done, works correctly."))
        self.assertIn("no_verification", [f.rule for f in no_verification(t)])

    def test_no_verification_silent_when_any_check_ran(self):
        t = transcript(tool("ruff check .", ok=False))
        self.assertEqual(no_verification(t), [])

    def test_scope_creep_counts_only_unrelated_files(self):
        t = transcript(edit("src/parser.py"), edit("a.py"), edit("b.py"), edit("c.py"))
        self.assertTrue(scope_creep(t))
        t2 = transcript(edit("src/parser.py"), edit("tests/test_parser.py"))
        self.assertEqual(scope_creep(t2), [])

    def test_retry_storm_needs_three_failures(self):
        t = transcript(*[tool("pytest tests/x.py", ok=False) for _ in range(3)])
        self.assertEqual([f.rule for f in retry_storm(t)], ["retry_storm"])
        self.assertEqual(retry_storm(transcript(tool("pytest", ok=False))), [])

    def test_risky_change_unflagged(self):
        t = transcript(edit("migrations/0042_auth.py"), edit("src/parser.py"),
                       tool("pytest", ok=True), text("Done: fixed the parser."))
        self.assertEqual([f.rule for f in risky_change_unflagged(t)], ["risky_change_unflagged"])
        t2 = transcript(edit("migrations/0042_auth.py"),
                        tool("pytest", ok=True),
                        text("Also touched the auth migration - needs review before deploy."))
        self.assertEqual(risky_change_unflagged(t2), [])

    def test_is_verification_recognises_toolchains(self):
        for command in ["python -m unittest", "npm test", "cargo test", "go test ./...",
                        "npx tsc --noEmit", "make check"]:
            with self.subTest(command=command):
                self.assertTrue(is_verification(parse_transcript(
                    {"task": "t", "steps": [tool(command)]}).tools[0]))
        self.assertFalse(is_verification(parse_transcript(
            {"task": "t", "steps": [tool("echo testing")]}).tools[0]))

    def test_findings_sorted_by_severity(self):
        t = parse_transcript({"task": "x", "steps": [
            {"kind": "tool", "command": "rm -rf /tmp/x", "ok": True},
            {"kind": "tool", "command": "pytest", "ok": False},
            {"kind": "text", "text": "done"},
        ]})
        findings = lint(t)
        severities = [f.severity for f in findings]
        self.assertEqual(severities, sorted(severities, key=["error", "warn", "info"].index))

    def test_parse_rejects_unknown_kind(self):
        with self.assertRaises(ValueError):
            parse_transcript({"task": "x", "steps": [{"kind": "telepathy"}]})
