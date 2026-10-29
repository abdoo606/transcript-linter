"""CLI: python -m tlinter lint --transcript samples/clean.json"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .model import load
from .rules import RULES, lint


def render(findings, path: str) -> str:
    if not findings:
        return f"{path}: clean (7 rules, no findings)\n"
    lines = [f"{path}: {len(findings)} finding(s)"]
    for f in findings:
        where = f" @step {f.step_index}" if f.step_index is not None else ""
        lines.append(f"  [{f.severity:5}] {f.rule}{where}: {f.message}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tlinter", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lint", help="lint one or more transcript files")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true", help="fail on warnings too")

    p_rules = sub.add_parser("rules", help="list rules")

    args = parser.parse_args(argv)

    if args.cmd == "rules":
        for name in RULES:
            print(name)
        return 0

    worst = 0
    for path in args.files:
        try:
            findings = lint(load(path))
        except (OSError, ValueError, KeyError) as exc:
            print(f"{path}: cannot parse ({exc})", file=sys.stderr)
            worst = max(worst, 3)
            continue
        if args.json:
            print(json.dumps({"transcript": str(path),
                              "findings": [f.as_dict() for f in findings]}, indent=2))
        else:
            sys.stdout.write(render(findings, str(path)))
        if any(f.severity == "error" for f in findings):
            worst = max(worst, 1)
        elif args.strict and findings:
            worst = max(worst, 1)
    return worst


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
