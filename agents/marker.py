#!/usr/bin/env python3
"""
CoachAI Marker Agent — rubric-grounded first-pass grading (Workflow 1).

Role: experienced HSC Enterprise Computing teacher / NESA-style marker.
Given a question, its marking guidelines (rubric), retrieved syllabus/TSR
context and a student answer, it awards a provisional mark and writes
structured feedback, returned as a dict:

    {
        "marks": int,            # provisional 0..max_marks
        "justification": str,    # why this mark (band matched, keywords hit/missed)
        "feedback": [{"type": "good"|"improve"|"rule", "text": str}, ...]
    }

All LLM calls go through agents.models.complete() (project-wide convention).
"""
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents.models import complete  # noqa: E402

SYSTEM_ROLE = (
    "You are an experienced HSC Enterprise Computing teacher and a senior marker "
    "familiar with NSW Education Standards Authority (NESA) marking guidelines. "
    "You grade extended-response answers strictly against the provided rubric "
    "mark bands. You reward precise syllabus terminology, correct use of concepts "
    "and answers that actually address every verb/requirement in the question "
    "(e.g. 'describe' needs more than 'outline'). You NEVER invent content that is "
    "not in the answer or the rubric, and you never give credit for irrelevant or "
    "bluffing material. You return ONLY a JSON object — no markdown, no prose."
)

FEEDBACK_TYPES = ("good", "improve", "rule")

# ------------------------------------------------------------------------- helpers

def build_rubric_text(question: dict) -> str:
    """Render a question's marking_guidelines into a compact rubric string."""
    mg = question.get("marking_guidelines") or []
    if mg:
        bands = sorted(mg, key=lambda g: _band_num(g.get("band")), reverse=True)
        return "\n".join(
            f"[{g.get('band', '?')} mark band] {str(g.get('criteria', '')).strip()}"
            for g in bands
        )
    return f"No detailed band criteria provided. Maximum {question.get('marks', '?')} marks."


def _band_num(band) -> int:
    try:
        return int(str(band).strip())
    except (TypeError, ValueError):
        return 0


def extract_json_block(text: str) -> dict:
    """Robustly pull the first JSON object out of a model reply.

    Handles: ```json fences, bare ``` fences, leading/trailing prose,
    and JSON that spans multiple lines. Raises ValueError when no valid
    JSON object can be found.
    """
    if not text or not text.strip():
        raise ValueError("empty model output")

    # 1) fenced code block carrying JSON (```json ... ``` or ``` ... ```)
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = []
    if fence:
        candidates.append(fence.group(1))
    # 2) balanced-brace scan from the first '{' to the last '}'
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    last_err = None
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError as exc:
            last_err = exc
    raise ValueError(f"no valid JSON object in model output: {last_err}")


def normalize_feedback(feedback) -> list:
    """Coerce arbitrary model feedback into [{type, text}] with allowed types."""
    if not isinstance(feedback, list):
        return []
    out = []
    for item in feedback:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        ftype = str(item.get("type", "improve")).strip().lower()
        if ftype not in FEEDBACK_TYPES:
            ftype = "improve"
        out.append({"type": ftype, "text": text})
    return out


def _doc_text(doc: dict, limit: int = 1200) -> str:
    """Compact a retrieved document for prompt context."""
    text = str(doc.get("text", "")).strip().replace("\r", "")
    return text[:limit] + ("…" if len(text) > limit else "")


# ----------------------------------------------------------------- prompt assembly

def build_marker_prompt(
    question: dict,
    rubric_text: str,
    retrieved_docs: list,
    student_answer: str,
    critique: str | None = None,
) -> tuple[str, str]:
    """Assemble (system, user) prompt pair for the marker agent.

    Args:
        question:      question dict from data/questions.json
                       (keys: id/text/marks/marking_guidelines/topics)
        rubric_text:   rendered marking guidelines (see build_rubric_text)
        retrieved_docs: RAG hits [{text, source, topic, score}] — syllabus grounding
        student_answer: the response being graded
        critique:      optional verifier critique fed back on retry rounds
    """
    system = SYSTEM_ROLE + (
        "\n\nOutput contract: reply with a single JSON object of the form\n"
        '{"marks": <int>, "justification": "<short audit of why this band was awarded / '
        'key terms present or missing>", "feedback": [{"type": "good"|"improve"|"rule", '
        '"text": "<one concrete, actionable comment>"}]}\n'
        "Rules: marks must be an integer between 0 and the maximum; feedback entries "
        "must be specific to THIS answer (never generic boilerplate); type 'good' = what "
        "the student did well, 'improve' = how to lift the answer, 'rule' = syllabus "
        "misconception or rule the student broke."
    )

    lines = []
    lines.append("=== QUESTION ===")
    lines.append(str(question.get("text", "")).strip())
    lines.append(f"\nQuestion id: {question.get('id', '?')}   Maximum marks: {question.get('marks', '?')}")
    lines.append("\n=== RUBRIC (NESA marking guidelines) ===")
    lines.append(rubric_text)

    docs = retrieved_docs or []
    if docs:
        lines.append("\n=== REFERENCE MATERIAL (retrieved from NESA syllabus/TSR; use it ONLY to "
                     "recognise correct terminology — do not require content the question does not ask for) ===")
        for i, d in enumerate(docs[:4], 1):
            src = d.get("source", "?")
            lines.append(f"[ref {i} | source: {src}] {_doc_text(d)}")
    else:
        lines.append("\n(No reference material retrieved for this question.)")

    lines.append("\n=== STUDENT ANSWER ===")
    answer = (student_answer or "").strip()
    lines.append(answer if answer else "(empty answer)")

    if critique:
        lines.append("\n=== QA AUDITOR CRITIQUE (from the previous verification round — address it "
                     "and re-grade accordingly) ===")
        lines.append(str(critique).strip())

    lines.append(
        "\nGrade the student answer now. Return ONLY the JSON object."
    )
    return system, "\n\n".join(lines)


# ----------------------------------------------------------------- grading

def mark(
    question_dict: dict,
    student_answer: str,
    retrieved_docs: list,
    critique: str | None = None,
    max_marks: int | None = None,
) -> dict:
    """Run the marker agent once (with one re-parse retry) and return the verdict dict."""
    max_marks = int(max_marks if max_marks is not None else question_dict.get("marks", 0) or 0)
    rubric_text = build_rubric_text(question_dict)
    system, user = build_marker_prompt(
        question_dict, rubric_text, retrieved_docs, student_answer, critique=critique
    )

    attempts = [
        ("0.5", ""),
        ("0.2", "\n\nIMPORTANT: your previous reply was not valid JSON. "
               "Reply with ONLY a JSON object, nothing else."),
    ]
    last_err = None
    for temp, extra in attempts:
        try:
            raw = complete(system, user + extra, temperature=float(temp))
            data = extract_json_block(raw)
            return _normalize_marker_output(data, max_marks)
        except Exception as exc:  # JSON parse / network blip -> one retry
            last_err = exc

    raise RuntimeError(f"[marker.mark] grading failed for {question_dict.get('id')}: {last_err}")


def _normalize_marker_output(data: dict, max_marks: int) -> dict:
    """Validate/coerce raw model JSON into the marker contract."""
    try:
        marks = int(float(data.get("marks", 0)))
    except (TypeError, ValueError):
        marks = 0
    marks = max(0, min(max_marks, marks))
    justification = str(data.get("justification", "")).strip()
    return {
        "marks": marks,
        "justification": justification or "(no justification given)",
        "feedback": normalize_feedback(data.get("feedback")),
        "max_marks": max_marks,
    }


if __name__ == "__main__":  # quick manual check
    import json as _json
    q = _json.load(open(os.path.join(_ROOT, "data/questions.json")))["questions"][1]
    out = mark(q, "Memes can be counted to see how popular the campaign is.", [], max_marks=q["marks"])
    print(_json.dumps(out, ensure_ascii=False, indent=2))
