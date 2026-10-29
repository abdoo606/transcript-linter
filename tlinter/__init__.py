"""transcript-linter: cheap, deterministic checks on coding-agent transcripts.

The point is not to replace human judgment (see ../agent-eval-harness) but to
catch the failure modes that are objective: a claim of "tests pass" with no
test run, a red test that was scrolled past, a destructive shell command.
"""
from .model import Finding, Transcript, parse_transcript
from .rules import RULES, lint

__all__ = ["Finding", "Transcript", "parse_transcript", "RULES", "lint"]
__version__ = "0.1.0"
