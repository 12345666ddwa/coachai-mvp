#!/usr/bin/env python3
"""
CoachAI Verifier Agent — NESA QA Auditor (Workflow 1, second pass).

Critically audits the marker's provisional verdict BEFORE it is shipped to a
student: recomputes the mark against the rubric, hunts for hallucinated
concepts / unsupported claims (grounded against the retrieved syllabus docs),
and checks the marker's marks against its own. Outputs the final verdict:

    {
        "final_marks": int,        # 0..max_marks after audit
        "is_approved": bool,       # True  -> ship result
                                   # False -> retry branch (or flag when exhausted)
        "confidence_pct": int,     # model self-report 0..100 (post-processed upstream)
        "refined_feedback": [{"type": ..., "text": ...}],
        "flags": [str]             # concrete criticisms to feed back to the marker
    }

All LLM calls go through agents.models.complete() (project-wide convention).
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents.marker import (  # noqa: E402
    _doc_text,
    build_rubric_text,
    extract_json_block,
    normalize_feedback,
)
from agents.models import complete  # noqa: E402

QA_ROLE = (
    "You are a NESA QA Auditor — a strict, sceptical quality-assurance reviewer "
    "for HSC Enterprise Computing marking. A marker agent has graded a student "
    "answer. Your job: 1) recompute the correct mark yourself against the rubric; "
    "2) catch hallucinated or off-syllabus concepts the marker credited; 3) check "
    "the marker's mark is consistent with its own justification and the rubric "
    "bands; 4) rewrite feedback so it is accurate and useful for the student. "
    "You approve ONLY verdicts you genuinely agree with after re-reading the "
    "rubric and the retrieved syllabus material. Remember this is a draft "
    "evaluation for teacher confirmation: keep your wording measured and "
    "evidence-based (what the response does or does not yet evidence), never "
    "absolute. You return ONLY a JSON object."
)


def build_verifier_prompt(
    question: dict,
    rubric_text: str,
    marker_output: dict,
    student_answer: str,
    retrieved_docs: list,
) -> tuple[str, str]:
    """Assemble (system, user) prompt pair for the verifier agent."""
    system = QA_ROLE + (
        "\n\nOutput contract: reply with a single JSON object of the form\n"
        '{"final_marks": <int>, "is_approved": <bool>, "confidence_pct": <int 0-100>, '
        '"refined_feedback": [{"type": "good"|"improve"|"rule", "text": "<comment>"}], '
        '"flags": ["<specific criticism to send back to the marker>", ...]}\n'
        "Rules: final_marks in 0..maximum; set is_approved=false whenever the mark is "
        "wrong, the justification contradicts the rubric, the marker credited invented "
        "content, or feedback would mislead the student — otherwise true. "
        "confidence_pct = how sure YOU are of the final verdict after auditing "
        "(not the marker's confidence). flags may be empty when approved. "
        "Keep every feedback text under 40 words and every flag under 25 words so the "
        "reply stays compact and complete."
    )

    lines = []
    lines.append("=== QUESTION ===")
    lines.append(str(question.get("text", "")).strip())
    lines.append(f"\nQuestion id: {question.get('id', '?')}   Maximum marks: {question.get('marks', '?')}")
    lines.append("\n=== RUBRIC (NESA marking guidelines) ===")
    lines.append(rubric_text)

    docs = retrieved_docs or []
    if docs:
        lines.append("\n=== SYLLABUS REFERENCE MATERIAL (grounding for hallucination check) ===")
        for i, d in enumerate(docs[:4], 1):
            lines.append(f"[ref {i} | source: {d.get('source', '?')}] {_doc_text(d)}")

    lines.append("\n=== MARKER'S PROVISIONAL VERDICT (audit this) ===")
    lines.append(
        f"marks awarded: {marker_output.get('marks')} / {marker_output.get('max_marks', '?')}\n"
        f"justification: {marker_output.get('justification', '')}\n"
        f"feedback: {marker_output.get('feedback', [])}"
    )

    lines.append("\n=== STUDENT ANSWER ===")
    answer = (student_answer or "").strip()
    lines.append(answer if answer else "(empty answer)")

    lines.append(
        "\nAudit now: recompute the mark, list every problem in 'flags', and give your "
        "final verdict. Return ONLY the JSON object."
    )
    return system, "\n\n".join(lines)


def verify(
    question_dict: dict,
    marker_output: dict,
    student_answer: str,
    retrieved_docs: list,
) -> dict:
    """Run the verifier agent once (one re-parse retry) and return the audit dict."""
    max_marks = int(question_dict.get("marks", 0) or 0)
    rubric_text = build_rubric_text(question_dict)
    system, user = build_verifier_prompt(
        question_dict, rubric_text, marker_output, student_answer, retrieved_docs
    )

    attempts = [
        ("0.2", ""),
        ("0.0", "\n\nIMPORTANT: your previous reply was not valid JSON. "
                "Reply with ONLY a JSON object, nothing else."),
    ]
    last_err = None
    for temp, extra in attempts:
        try:
            raw = complete(system, user + extra, temperature=float(temp), max_tokens=8192)
            data = extract_json_block(raw)
            return _normalize_verifier_output(data, marker_output, max_marks)
        except Exception as exc:
            last_err = exc

    raise RuntimeError(f"[verifier.verify] audit failed for {question_dict.get('id')}: {last_err}")


def _normalize_verifier_output(data: dict, marker_output: dict, max_marks: int) -> dict:
    """Validate/coerce raw model JSON into the verifier contract."""
    try:
        final_marks = int(float(data.get("final_marks", marker_output.get("marks", 0))))
    except (TypeError, ValueError):
        final_marks = int(marker_output.get("marks", 0))
    final_marks = max(0, min(max_marks, final_marks))

    approved_raw = str(data.get("is_approved", "true")).strip().lower()
    is_approved = approved_raw in ("true", "yes", "1", "approved")

    try:
        confidence = int(float(data.get("confidence_pct", 70)))
    except (TypeError, ValueError):
        confidence = 70
    confidence = max(0, min(100, confidence))

    flags = data.get("flags", [])
    if not isinstance(flags, list):
        flags = []
    flags = [str(f).strip() for f in flags if str(f).strip()]

    refined = normalize_feedback(data.get("refined_feedback"))
    if not refined:  # fall back to marker feedback when verifier returned none
        refined = marker_output.get("feedback", []) or []

    return {
        "final_marks": final_marks,
        "is_approved": is_approved,
        "confidence_pct": confidence,
        "refined_feedback": refined,
        "flags": flags,
    }


if __name__ == "__main__":  # quick manual check
    import json as _json
    q = _json.load(open(os.path.join(_ROOT, "data/questions.json")))["questions"][1]
    pseudo_marker = {
        "marks": 1, "max_marks": q["marks"],
        "justification": "some relevant info only",
        "feedback": [{"type": "improve", "text": "add quantification"}],
    }
    out = verify(q, pseudo_marker, "Memes are funny pictures.", [])
    print(_json.dumps(out, ensure_ascii=False, indent=2))
