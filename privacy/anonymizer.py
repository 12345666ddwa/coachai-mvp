#!/usr/bin/env python3
"""
CoachAI — privacy.anonymizer: deterministic PII anonymisation before LLM calls
==============================================================================

Team rule for CoachAI: raw student data must be anonymised BEFORE it is sent
to any hosted LLM. This module is the single, dependency-free implementation
of that rule for the grading pipeline.

Why no NER / ML model?
----------------------
A generic named-entity model is noisy on exam prose — it happily tags "Will"
in "Will the ban reduce supply?" as a person. A false positive silently
corrupts a student's answer before the marker ever sees it, which is worse
than a rare missed name the caller forgot to list. So this module only
replaces what it can be *certain* about:

    1. student names supplied by the caller (the most reliable source),
    2. email addresses (high-precision regex),
    3. Australian phone numbers (high-precision regex),
    4. school names, when the caller supplies them.

Contract
--------
* Placeholders are numbered per category, ordered by first appearance:
  ``[STUDENT_1]``, ``[STUDENT_2]``, ``[EMAIL_1]``, ``[PHONE_1]``,
  ``[SCHOOL_1]``, ...
* The same original value always receives the same placeholder for the whole
  batch (one ``anonymize()`` call, or one ``anonymize_result()`` walk).
* The returned mapping (placeholder -> original value) makes the operation
  reversible via :func:`restore` / :func:`restore_result`; restore the real
  values only in the final local report, never in text sent to the LLM.
* Matching is case-insensitive. ASCII names are anchored on ``\\b`` word
  boundaries so "Ann" never matches inside "Announcement". CJK names are
  matched as plain substrings — ``\\b`` is unreliable next to CJK characters
  and Chinese text has no space-delimited word boundaries anyway.
* When two candidates overlap, the longer match at the earlier position wins
  (so the email "smith@example.com" is not half-eaten by the name "Smith",
  and "Alex Chen" beats "Alex").

Usage
-----
    from privacy import anonymizer

    safe_text, mapping = anonymizer.anonymize(text, student_names=["Alex Chen"])
    #  ... send safe_text to the LLM ...
    real_text = anonymizer.restore(llm_output, mapping)

    # grading-pipeline result dicts (nested dicts / lists of feedback items):
    safe_result, mapping = anonymizer.anonymize_result(result, student_names=[...])
    result_again = anonymizer.restore_result(safe_result, mapping)
"""

from __future__ import annotations

import re
from typing import Any, Callable, Iterable, Optional, Pattern

__all__ = ["anonymize", "restore", "anonymize_result", "restore_result"]

# ---------------------------------------------------------------------------
# Regex building blocks
# ---------------------------------------------------------------------------

# Common email shape. Precision over RFC completeness: exotic-but-legal
# addresses may not match, and that is an accepted trade-off.
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# Australian phone numbers — two high-precision shapes:
#   mobile:   "0412 345 678" / "0412345678" / "+61 412 345 678" / "61-412-345-678"
#   landline: "(02) 9876 5432"
_PHONE_PATTERNS: tuple[Pattern[str], ...] = (
    re.compile(r"(?:\+?61|0)[\s-]?4\d{2}[\s-]?\d{3}[\s-]?\d{3}"),
    re.compile(r"\(0\d\)\s?\d{4}\s?\d{4}"),
)

# Placeholder categories. Order doubles as the deterministic tie-break when
# two sources match the exact same span (student wins over school).
_CATS: tuple[str, ...] = ("STUDENT", "SCHOOL", "EMAIL", "PHONE")
_CAT_PRIORITY = {name: i for i, name in enumerate(_CATS)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _as_name_list(names: Optional[Iterable[str]]) -> list[str]:
    """Normalise caller input to a clean list of names.

    Accepts None, a single string (treated as one name) or an iterable of
    strings. Blank entries are dropped; surrounding whitespace is stripped.
    """
    if not names:
        return []
    if isinstance(names, str):
        names = [names]
    out: list[str] = []
    for name in names:
        if isinstance(name, str) and name.strip():
            out.append(name.strip())
    return out


def _name_regex(name: str) -> Pattern[str]:
    """Build the match pattern for one name.

    ASCII names get ``\\b...\\b`` so "Ann" cannot match inside "Announcement".
    Non-ASCII (e.g. CJK) names fall back to a plain substring match: regex
    word boundaries behave unreliably next to CJK characters, and Chinese
    text has no space-delimited word boundaries to anchor on.
    """
    escaped = re.escape(name)
    if name.isascii():
        return re.compile(rf"\b{escaped}\b", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


def _walk(value: Any, fn: Callable[[str], str]) -> Any:
    """Rebuild ``value`` applying ``fn`` to every string found inside.

    Recurses into dict values (keys are schema field names and are left
    untouched), lists and tuples. Scalars (int/float/bool/None/...) pass
    through unchanged. New containers are built — the input is never mutated.
    """
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, dict):
        return {key: _walk(item, fn) for key, item in value.items()}
    if isinstance(value, list):
        return [_walk(item, fn) for item in value]
    if isinstance(value, tuple):
        return tuple(_walk(item, fn) for item in value)
    return value


# ---------------------------------------------------------------------------
# Stateful engine (keeps placeholder numbering stable across a batch)
# ---------------------------------------------------------------------------

class _Anonymizer:
    """Numbering state for one batch: a single text, or one result-dict walk."""

    def __init__(self, student_names: Optional[Iterable[str]] = None,
                 school_names: Optional[Iterable[str]] = None) -> None:
        # category -> casefolded original value -> placeholder
        self._seen: dict[str, dict[str, str]] = {cat: {} for cat in _CATS}
        self._counters: dict[str, int] = {cat: 0 for cat in _CATS}
        # placeholder -> original value (returned to the caller)
        self.mapping: dict[str, str] = {}
        # (category, compiled pattern) pairs for caller-supplied names
        self._name_patterns: list[tuple[str, Pattern[str]]] = []
        for cat, names in (("STUDENT", student_names), ("SCHOOL", school_names)):
            for name in _as_name_list(names):
                self._name_patterns.append((cat, _name_regex(name)))

    # -- public -------------------------------------------------------------

    def anonymize_text(self, text: str) -> str:
        """Replace every confident PII match in ``text`` with placeholders."""
        accepted = self._find_matches(text)
        if not accepted:
            return text
        pieces: list[str] = []
        cursor = 0
        for start, end, cat, value in accepted:
            pieces.append(text[cursor:start])
            pieces.append(self._placeholder_for(cat, value))
            cursor = end
        pieces.append(text[cursor:])
        return "".join(pieces)

    # -- internals ----------------------------------------------------------

    def _find_matches(self, text: str) -> list[tuple[int, int, str, str]]:
        """Collect non-overlapping PII candidates as (start, end, cat, value).

        Overlap policy: sort by position with longer matches first and
        greedily accept anything that does not overlap an accepted match.
        This keeps the full email "smith@example.com" from being half-eaten
        by the student name "Smith", and prefers "Alex Chen" over "Alex".
        """
        candidates: list[tuple[int, int, str, str]] = []

        for m in _EMAIL_RE.finditer(text):
            # Never swallow the sentence period: domains cannot end in "." or "-".
            value = m.group(0).rstrip(".-")
            if value:
                candidates.append((m.start(), m.start() + len(value), "EMAIL", value))

        for pattern in _PHONE_PATTERNS:
            for m in pattern.finditer(text):
                candidates.append((m.start(), m.end(), "PHONE", m.group(0)))

        for cat, pattern in self._name_patterns:
            for m in pattern.finditer(text):
                candidates.append((m.start(), m.end(), cat, m.group(0)))

        candidates.sort(key=lambda c: (c[0], -(c[1] - c[0]), _CAT_PRIORITY[c[2]]))

        accepted: list[tuple[int, int, str, str]] = []
        last_end = -1
        for start, end, cat, value in candidates:
            if start >= last_end:          # skip anything overlapping the last accept
                accepted.append((start, end, cat, value))
                last_end = end
        return accepted

    def _placeholder_for(self, cat: str, value: str) -> str:
        """Return the stable placeholder for ``value``.

        Numbers are assigned the first time a value (case-insensitively) is
        seen; every later occurrence reuses the same placeholder. The mapping
        stores the first-seen surface form so restore() reproduces the text
        as it originally appeared.
        """
        key = value.casefold()
        by_key = self._seen[cat]
        placeholder = by_key.get(key)
        if placeholder is None:
            self._counters[cat] += 1
            placeholder = f"[{cat}_{self._counters[cat]}]"
            by_key[key] = placeholder
            self.mapping[placeholder] = value
        return placeholder


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def anonymize(text: str, student_names: Optional[Iterable[str]] = None,
              school_names: Optional[Iterable[str]] = None) -> tuple[str, dict]:
    """Replace PII with placeholders. Returns (sanitized_text, mapping).

    mapping: {'[STUDENT_1]': 'Alex Chen', '[EMAIL_1]': 'x@y.com', ...}
    The same original value always maps to the same placeholder. Empty (or
    non-string) input is returned unchanged with an empty mapping.
    """
    if not isinstance(text, str) or not text:
        return text, {}
    state = _Anonymizer(student_names, school_names)
    return state.anonymize_text(text), state.mapping


def restore(text: str, mapping: dict) -> str:
    """Replace placeholders back with original values.

    Unknown placeholders are left as-is. An empty (or missing) mapping is a
    no-op. Placeholders are replaced longest-first so "[STUDENT_10]" can
    never be damaged by a "[STUDENT_1]" replacement.
    """
    if not isinstance(text, str) or not text or not mapping:
        return text
    for placeholder in sorted(mapping, key=lambda p: (-len(p), p)):
        text = text.replace(placeholder, mapping[placeholder])
    return text


def anonymize_result(result: dict, student_names: Optional[Iterable[str]] = None,
                     school_names: Optional[Iterable[str]] = None) -> tuple[dict, dict]:
    """Anonymize every string inside a grading-pipeline result dict.

    Walks dict values, strings inside lists of dicts (e.g. feedback items)
    and nested lists/tuples, sharing one numbering state so the same student
    name maps to the same placeholder across all fields. Returns a new dict;
    the input is never mutated.
    """
    state = _Anonymizer(student_names, school_names)
    return _walk(result, state.anonymize_text), state.mapping


def restore_result(result: dict, mapping: dict) -> dict:
    """Restore all strings in a result dict using ``mapping``.

    Same traversal rules as :func:`anonymize_result`; returns a new dict and
    never mutates the input.
    """
    return _walk(result, lambda s: restore(s, mapping))
