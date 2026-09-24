"""
CoachAI — privacy package.
==========================

Public surface of the Phase-2 privacy layer: deterministic PII anonymisation
before any student text is sent to a hosted LLM.

    from privacy import anonymize, restore
    from privacy import anonymizer          # module access also supported

Hard rule (team decision): raw student data never leaves the process in
cleartext — anonymise first, send to the model, then restore real names
locally in the final report.
"""

from . import anonymizer
from .anonymizer import anonymize, anonymize_result, restore, restore_result

__all__ = [
    "anonymize",
    "restore",
    "anonymize_result",
    "restore_result",
    "anonymizer",
]
