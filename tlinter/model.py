"""Transcript model: a task plus an ordered list of agent actions."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Role = Literal["assistant", "user", "tool"]


@dataclass(frozen=True)
class Step:
    index: int
    role: Role
    kind: str            # text | tool | edit
    text: str = ""
    tool: str = ""
    command: str = ""
    path: str = ""
    ok: bool | None = None


@dataclass(frozen=True)
class Transcript:
    task: str
    steps: tuple[Step, ...] = ()

    @property
    def texts(self) -> list[Step]:
        return [s for s in self.steps if s.kind == "text"]

    @property
    def tools(self) -> list[Step]:
        return [s for s in self.steps if s.kind == "tool"]

    @property
    def edits(self) -> list[Step]:
        return [s for s in self.steps if s.kind == "edit"]

    def last_text(self) -> Step | None:
        return self.texts[-1] if self.texts else None

    def after(self, index: int) -> list[Step]:
        return [s for s in self.steps if s.index > index]


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Literal["error", "warn", "info"]
    message: str
    step_index: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "severity": self.severity,
                "message": self.message, "step_index": self.step_index}


def parse_transcript(data: dict[str, Any]) -> Transcript:
    if "task" not in data:
        raise ValueError("transcript missing 'task'")
    raw_steps: list[dict[str, Any]] = data.get("steps") or data.get("messages") or []
    steps: list[Step] = []
    for i, raw in enumerate(raw_steps):
        kind = raw.get("kind", "text")
        if kind not in {"text", "tool", "edit"}:
            raise ValueError(f"step {i}: unknown kind {kind!r}")
        steps.append(Step(
            index=i,
            role=raw.get("role", "assistant"),
            kind=kind,
            text=raw.get("text", ""),
            tool=raw.get("tool", ""),
            command=raw.get("command", ""),
            path=raw.get("path", ""),
            ok=raw.get("ok"),
        ))
    return Transcript(task=str(data["task"]), steps=tuple(steps))


def load(path: str | Path) -> Transcript:
    return parse_transcript(json.loads(Path(path).read_text(encoding="utf-8")))
