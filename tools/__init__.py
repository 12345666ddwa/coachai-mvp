"""CoachAI tooling package - standalone processing helpers.

Exposes :mod:`tools.transcript_analyzer` (Phase 6b lesson recording review):

    from tools.transcript_analyzer import transcribe_audio, analyze_lesson

Note: this package needs an explicit __init__.py because some environments
ship an unrelated regular `tools` package in site-packages, which would
otherwise shadow this directory (a namespace package loses to a regular one).
"""

from . import transcript_analyzer  # noqa: F401

__all__ = ["transcript_analyzer"]
