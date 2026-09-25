#!/usr/bin/env python3
"""
CoachAI Report Writer Agent (Phase 5): NSW-style report comments.

Input:  a student (from store.db), their marking history + aggregate summary,
        and the teacher's own notes for the reporting period.

Output: one report comment dict

    {
        "student_id": int,
        "student_name": str,
        "period": str,
        "comment": str,            # the report comment (student name, third person)
        "evidence": [str, ...],    # concrete evidence the comment was built from
        "self_eval_note": str,     # a prompt the student can reflect on
        "teacher_notes": str,      # passed through for saving alongside the comment
    }

Writing guidelines enforced via the prompt (NSW report practice):
    * refer to the student by name in the third person, never "I" / "you";
    * strengths first, then areas for improvement;
    * link to course outcomes / syllabus language;
    * evidence-based wording drawn only from the supplied records;
    * correct gender pronouns (he / she / they).

All LLM calls go through agents.models.complete() (project-wide convention).
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents.marker import extract_json_block  # noqa: E402
from agents.models import complete  # noqa: E402
from store import db  # noqa: E402

# Pronoun triples keyed by the store's gender codes; anything else -> they/them.
PRONOUNS = {
    "M": ("he", "him", "his"),
    "F": ("she", "her", "her"),
}
DEFAULT_PRONOUNS = ("they", "them", "their")

HISTORY_LIMIT = 10          # most recent submissions rendered into the prompt
EVIDENCE_LIMIT = 6          # keep evidence bullets short and specific
COMMENT_MAX_CHARS = 6000    # guard against runaway model output

SYSTEM_ROLE = (
    "You are an experienced NSW (Australia) secondary school teacher writing a "
    "formal student report comment for a school report. You write in clear, "
    "professional teacher voice following these rules:\n"
    "1. Third person only: refer to the student by name (or 'he' / 'she' / 'they'); "
    "never use 'I' or address the student as 'you'.\n"
    "2. Strengths first: open with what the student has done well this period, "
    "then move to areas for improvement in a constructive, forward-looking tone.\n"
    "3. Link learning to the course: connect comments to Enterprise Computing "
    "course outcomes and skills (for example using terminology such as "
    "algorithmic thinking, data handling, cybersecurity, project work) where the "
    "evidence supports it.\n"
    "4. Evidence-based language: base every claim on the assessment records and "
    "the teacher notes provided. Describe what the student did or did not yet "
    "evidence; never invent achievements, scores or incidents.\n"
    "5. Use the correct pronouns supplied for the student.\n"
    "6. Weave the teacher's own notes in naturally: they take priority over "
    "generic phrasing and must not be ignored or contradicted.\n"
    "7. Write 2 to 4 tight sentences (roughly 60 to 130 words). No bullet "
    "points, no markdown, no emoji."
)


# --------------------------------------------------------------------------- helpers

def pronouns_for(gender) -> dict:
    """Return {'subject','object','possessive'} for a store gender code."""
    key = str(gender or "").strip().upper()
    subject, obj, poss = PRONOUNS.get(key, DEFAULT_PRONOUNS)
    return {"subject": subject, "object": obj, "possessive": poss}


def _fmt_rate(rate) -> str:
    """0.6667 -> '67%'; None -> 'n/a'."""
    if rate is None:
        return "n/a"
    try:
        return f"{round(float(rate) * 100)}%"
    except (TypeError, ValueError):
        return "n/a"


def _history_lines(history: list) -> list:
    """Render the most recent usable submissions as compact 'qid: 2/3 (67%)' lines."""
    lines = []
    for sub in list(history)[-HISTORY_LIMIT:]:
        qid = sub.get("question_id", "?")
        marks = sub.get("marks_awarded")
        max_marks = sub.get("max_marks")
        status = sub.get("status") or "approved"
        if marks is None or not max_marks:
            lines.append(f"- {qid}: no usable mark recorded (status: {status})")
            continue
        pct = _fmt_rate(float(marks) / float(max_marks) if max_marks else None)
        lines.append(f"- {qid}: {marks}/{max_marks} ({pct}), status: {status}")
    return lines or ["- (no assessment records for this student yet)"]


def _question_lines(summary: dict) -> list:
    """Per-question averages from the store summary, as prompt lines."""
    lines = []
    for q in summary.get("by_question") or []:
        lines.append(
            f"- {q.get('question_id')}: {q.get('attempts')} attempt(s), "
            f"average {_fmt_rate(q.get('avg_score_rate'))} "
            f"({q.get('avg_marks')}/{q.get('max_marks')})"
        )
    return lines or ["- (no per-question averages available)"]


# --------------------------------------------------------------------------- prompt

def build_report_prompt(
    student: dict,
    summary: dict,
    history: list,
    period: str,
    teacher_notes: str = "",
    extra_notes: str = "",
) -> tuple:
    """Assemble (system, user) prompt pair for the report writer agent.

    Pure function: no db access, no LLM calls, safe to unit test directly.
    """
    pron = pronouns_for(student.get("gender"))
    name = str(student.get("name") or "The student").strip()
    year = str(student.get("year") or "(year not recorded)").strip()
    period_txt = str(period or "").strip() or "(period not specified)"

    system = SYSTEM_ROLE + (
        "\n\nOutput contract: reply with a single JSON object of the form\n"
        '{"comment": "<the report comment>", "evidence": ["<short factual basis '
        'for a claim made in the comment>"], "self_eval_note": "<one reflection '
        'prompt the student could answer>"}\n'
        "Rules: evidence must have 2 to 4 entries, each grounded in the records "
        "below (reference a question id or a score where possible); the "
        "self_eval_note is one short first-person question the student can "
        "answer about their learning. Do not add fields. No markdown."
    )

    lines = []
    lines.append("=== STUDENT ===")
    lines.append(f"Name: {name}")
    lines.append(f"Year: {year}")
    lines.append(f"Reporting period: {period_txt}")
    lines.append(
        f"Pronouns to use for {name}: {pron['subject']} / {pron['object']} / "
        f"{pron['possessive']} (third person must be used throughout)."
    )

    lines.append("\n=== ASSESSMENT SUMMARY (computed from the marking records) ===")
    total = summary.get("total_submissions", 0)
    lines.append(f"Total submissions recorded: {total}")
    lines.append(f"Average score rate: {_fmt_rate(summary.get('avg_score_rate'))}")
    lines.append("Per-question averages:")
    lines.extend(_question_lines(summary))

    lines.append("\n=== RECENT ASSESSMENT RECORDS (oldest to newest, up to "
                 f"{HISTORY_LIMIT}) ===")
    lines.extend(_history_lines(history))
    if not history:
        lines.append("NOTE: this student has no marking records yet. Write a "
                     "short, cautious comment based on the teacher notes only, "
                     "and do not invent progress that is not evidenced.")

    notes = (teacher_notes or "").strip()
    if notes:
        lines.append("\n=== TEACHER NOTES (weave these in naturally; they take "
                     "priority over generic phrasing) ===")
        lines.append(notes)
    else:
        lines.append("\n(No teacher notes provided - base the comment on the "
                     "assessment records only.)")

    extra = (extra_notes or "").strip()
    if extra:
        lines.append("\n=== ADDITIONAL CONTEXT (optional background; use only "
                     "where it helps) ===")
        lines.append(extra)

    lines.append("\nWrite the report comment for this period as a DRAFT for the "
                 "teacher to review and edit. Return ONLY the JSON object.")
    return system, "\n\n".join(lines)


# --------------------------------------------------------------------------- normalisation

def _normalize_output(data: dict, student: dict, period: str,
                      teacher_notes: str) -> dict:
    """Validate/coerce raw model JSON into the report-comment contract.

    Raises ValueError when the output is too thin (no comment text), which
    lets generate_report_comment retry once with a stricter instruction.
    """
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")

    comment = str(data.get("comment", "")).strip()
    if not comment:
        raise ValueError("model output has no comment text")
    comment = comment[:COMMENT_MAX_CHARS]

    evidence = [str(e).strip() for e in (data.get("evidence") or []) if str(e).strip()]
    return {
        # Identity fields are forced from the database, never trusted from the model.
        "student_id": student.get("id"),
        "student_name": str(student.get("name") or "").strip(),
        "period": str(period or "").strip(),
        "comment": comment,
        "evidence": evidence[:EVIDENCE_LIMIT],
        "self_eval_note": str(data.get("self_eval_note", "")).strip(),
        "teacher_notes": str(teacher_notes or "").strip(),
    }


# --------------------------------------------------------------------------- generation

def generate_report_comment(
    student_id: int,
    period: str,
    teacher_notes: str = "",
    extra_notes: str = "",
) -> dict:
    """Generate one report comment for a student (with one retry).

    Args:
        student_id:    Target student id (must exist in store.db).
        period:        Reporting period, e.g. "Term 3 2026".
        teacher_notes: The teacher's own points to weave in (optional).
        extra_notes:   Additional background context (optional).

    Returns:
        The report-comment dict (see module docstring). Students with no
        marking records still get a safe, notes-based comment.

    Raises:
        ValueError:   student_id unknown.
        RuntimeError: LLM call failed or produced no usable JSON after retry.
    """
    student = db.get_student(student_id)
    if not student:
        raise ValueError(f"[report_writer] unknown student_id: {student_id}")

    summary = db.get_student_summary(student_id)
    history = db.get_student_history(student_id)

    system, user = build_report_prompt(
        student, summary, history, period,
        teacher_notes=teacher_notes, extra_notes=extra_notes,
    )

    attempts = [
        (0.4, ""),
        (0.2, "\n\nIMPORTANT: your previous reply was not valid JSON or had no "
              "comment text. Reply with ONLY one complete JSON object, nothing else."),
    ]
    last_err = None
    for temp, extra in attempts:
        try:
            raw = complete(system, user + extra, temperature=float(temp))
            data = extract_json_block(raw)
            return _normalize_output(data, student, period, teacher_notes)
        except Exception as exc:  # noqa: BLE001 - parse/validation blip -> one retry
            last_err = exc

    raise RuntimeError(
        f"[report_writer.generate_report_comment] failed for student_id="
        f"{student_id} period={period!r}: {last_err}"
    )


if __name__ == "__main__":  # quick manual check (requires a real API key)
    import json as _json
    out = generate_report_comment(1, "Term 3 2026",
                                  teacher_notes="Improved confidence in class discussion.")
    print(_json.dumps(out, ensure_ascii=False, indent=2))
