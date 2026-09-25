#!/usr/bin/env python3
"""
CoachAI Student Coach Agent (Phase 6a): targeted practice + syllabus Q&A.

Two student-facing services, both grounded the same way lesson planning is:
the model may only build on the ticked syllabus dot points, the student's
weak areas, and the retrieved NESA TSR material (RAG). This is a
"repository of truth" component: when the retrieved material does not cover
a question, the answer must say so plainly instead of inventing content.

generate_practice(focus_dot_points, weak_areas, year, count, lang) -> dict
    {
        "questions": [
            {"question": str, "marks": int, "criteria": [str], "hint": str},
            ...
        ],
        "focus": [str],   # the dot points / weak areas the set targets
    }

    Questions imitate HSC exam style: a short scenario plus one clear
    directive verb. Criteria state what earns each mark; hints only nudge.

answer_question(student_question, context_note, year, lang) -> dict
    {
        "answer": str,     # grounded explanation; admits gaps instead of inventing
        "sources": [str],  # unique sources of the RAG documents actually consulted
        "note": str,       # short tip: terminology, common trap, next step
    }

All LLM calls go through agents.models.complete() (project-wide convention).

Typical usage:

    from agents.student_coach import generate_practice, answer_question
    set_ = generate_practice(["Explain how UI impacts on UX"], count=3)
    ans = answer_question("Why is lossy compression used for streaming?")
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents.marker import extract_json_block  # noqa: E402
from agents.models import complete  # noqa: E402

RAG_K = 4               # retrieved TSR chunks per call
DOC_LIMIT = 1200        # max characters per retrieved chunk in the prompt
COUNT_MIN = 1           # practice set size bounds (UI slider uses the same range)
COUNT_MAX = 5
COUNT_DEFAULT = 3       # used when the caller passes an unusable count
MARKS_MIN = 1           # per-question mark bounds
MARKS_MAX = 10
HINT_MAX_CHARS = 300
NOTE_MAX_CHARS = 600

LANG_NAME = {"en": "English", "zh": "Simplified Chinese (简体中文)"}

SYSTEM_ROLE_PRACTICE = (
    "You are an experienced HSC Enterprise Computing teacher in New South Wales, "
    "Australia, writing original practice questions for one student. "
    "Every question imitates the style of HSC examination questions: it opens "
    "with a short scenario or stimulus tied to the stated syllabus dot points, "
    "uses a single clear directive verb (describe, explain, compare, analyse, "
    "justify, evaluate, design), and is answerable within the marks it carries. "
    "You never copy a past paper question word for word and never step outside "
    "the syllabus dot points you were given. Your marking criteria mirror NESA "
    "style band descriptors: they state exactly what earns each mark. "
    "A hint only nudges the student towards the idea; it never gives the answer "
    "away. You return ONLY a JSON object, no markdown, no prose."
)

SYSTEM_ROLE_ANSWER = (
    "You are an experienced HSC Enterprise Computing teacher in New South Wales, "
    "Australia, answering one student's question about the course. "
    "The retrieved NESA / TSR material provided is your repository of truth: "
    "base every syllabus claim only on the supplied material and the stated "
    "course context, and use precise syllabus terminology. When the supplied "
    "material does not cover part of the question, say so plainly (for example, "
    "state that the provided course material does not cover that point) instead "
    "of inventing content; at most you may add a clearly labelled general study "
    "tip. You never fabricate syllabus references, outcome codes or mark values. "
    "You return ONLY a JSON object, no markdown, no prose."
)


# ----------------------------------------------------------------- retrieval

def retrieve_context(query: str, k: int = RAG_K) -> list:
    """RAG over the NESA TSR collection; [] when retrieval is unavailable.

    Retrieval must never kill practice generation or Q&A (same soft-fail
    policy as lesson_planner and mark_graph).
    """
    try:
        from rag.retriever import search
        return search(query, k=k) or []
    except Exception as exc:  # noqa: BLE001
        print(f"[student_coach] RAG retrieval unavailable, continuing without docs: {exc}")
        return []


def _doc_text(doc: dict, limit: int = DOC_LIMIT) -> str:
    """Compact a retrieved document for prompt context."""
    text = str(doc.get("text", "")).strip().replace("\r", "")
    return text[:limit] + ("…" if len(text) > limit else "")


def _doc_sources(docs: list) -> list:
    """Unique, ordered source labels from the retrieved docs (placeholders skipped)."""
    out, seen = [], set()
    for doc in docs or []:
        src = str(doc.get("source", "")).strip() if isinstance(doc, dict) else ""
        if not src or src == "?" or src in seen:
            continue
        seen.add(src)
        out.append(src)
    return out


def _clean_items(items) -> list:
    """Normalise a raw list into deduped non-empty strings (dicts use 'text')."""
    out, seen = [], set()
    for it in items or []:
        text = str(it.get("text", "")).strip() if isinstance(it, dict) else str(it).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


# ----------------------------------------------------------------- prompt assembly

def build_practice_prompt(
    focus_items: list,
    weak_items: list,
    year: str,
    count: int,
    lang: str,
    retrieved_docs: list,
) -> tuple:
    """Assemble (system, user) prompt pair for practice-question generation.

    Args:
        focus_items:    ticked syllabus dot point texts (may be empty when the
                        set targets weak areas only).
        weak_items:     weak-area descriptions from agents.tracker (may be empty).
        year:           "Year 11" / "Year 12".
        count:          how many questions to generate (already clamped).
        lang:           "en" / "zh" output language.
        retrieved_docs: RAG hits [{text, source, topic, score}] for grounding.
    """
    lang_name = LANG_NAME.get(lang, LANG_NAME["en"])
    system = SYSTEM_ROLE_PRACTICE + (
        "\n\nOutput contract: reply with a single JSON object of the form\n"
        '{"questions": [{"question": "<HSC-style question with a short scenario '
        'and one directive verb>", "marks": <int>, "criteria": ["<what earns the '
        'mark>", "..."], "hint": "<one nudge, never the answer>"}]}\n'
        f"Rules: exactly {count} question(s); marks must be an integer between "
        f"{MARKS_MIN} and {MARKS_MAX}; give 2 to 5 criteria per question, each "
        "tied to how the marks are earned; the hint is at most two sentences. "
        "Do not add fields."
    )

    lines = []
    lines.append("=== PRACTICE REQUEST ===")
    lines.append(f"Year: {year}")
    lines.append(f"Questions requested: {count}")
    lines.append("\nSyllabus dot points to target "
                 "(every question must trace back to these):")
    if focus_items:
        for i, item in enumerate(focus_items, 1):
            lines.append(f"{i}. {item}")
    else:
        lines.append("(none supplied; target the student weak areas below instead)")

    focus_lower = {str(f).strip().lower() for f in (focus_items or [])}
    shown_weak = [w for w in (weak_items or [])
                  if str(w).strip().lower() not in focus_lower]
    if shown_weak:
        lines.append("\nStudent weak areas to target (evidence from marking history):")
        for w in shown_weak:
            lines.append(f"- {w}")

    docs = retrieved_docs or []
    if docs:
        lines.append("\n=== RETRIEVED NESA / TSR CONTEXT (use it for accurate "
                     "terminology and command verbs; do not treat it as compulsory "
                     "content) ===")
        for i, d in enumerate(docs[:RAG_K], 1):
            src = d.get("source", "?") if isinstance(d, dict) else "?"
            lines.append(f"[ref {i} | source: {src}] {_doc_text(d)}")
    else:
        lines.append("\n(No TSR context retrieved; build the questions from the "
                     "syllabus dot points and your own expertise.)")

    lines.append("\n=== OUTPUT LANGUAGE ===")
    lines.append(f"Write every human-readable string (question, criteria, hint) "
                 f"in {lang_name}. Keep official syllabus terms, module names and "
                 "product names in their original form.")

    lines.append("\nProduce the practice set as a DRAFT for the student to attempt. "
                 "Return ONLY the JSON object.")
    return system, "\n\n".join(lines)


def build_answer_prompt(
    student_question: str,
    context_note: str,
    year: str,
    lang: str,
    retrieved_docs: list,
) -> tuple:
    """Assemble (system, user) prompt pair for the Q&A (repository of truth) agent.

    Args:
        student_question: the student's question (concept doubt / why an answer
                          was wrong).
        context_note:     optional context, e.g. "I just got Q4 wrong".
        year:             "Year 11" / "Year 12".
        lang:             "en" / "zh" output language.
        retrieved_docs:   RAG hits [{text, source, topic, score}] for grounding.
    """
    lang_name = LANG_NAME.get(lang, LANG_NAME["en"])
    system = SYSTEM_ROLE_ANSWER + (
        "\n\nOutput contract: reply with a single JSON object of the form\n"
        '{"answer": "<grounded explanation>", "note": "<one short tip>"}\n'
        "Rules: answer only from the supplied material and the stated course "
        "context; when that material does not cover the question, say so "
        "explicitly in the answer field instead of inventing content; the note "
        "is optional (use an empty string when there is nothing useful to add) "
        "and gives one short tip such as a terminology definition, a common "
        "mistake, or a next step. Plain text only; no markdown, no emoji, "
        "no extra fields."
    )

    lines = []
    lines.append("=== STUDENT QUESTION ===")
    lines.append(str(student_question or "").strip())
    note = str(context_note or "").strip()
    if note:
        lines.append("\n=== CONTEXT NOTE (from the student) ===")
        lines.append(note)
    lines.append(f"\nYear level: {year}")

    docs = retrieved_docs or []
    if docs:
        lines.append("\n=== NESA / TSR MATERIAL (your repository of truth; cite "
                     "ref numbers such as [ref 1] where useful) ===")
        for i, d in enumerate(docs[:RAG_K], 1):
            src = d.get("source", "?") if isinstance(d, dict) else "?"
            lines.append(f"[ref {i} | source: {src}] {_doc_text(d)}")
    else:
        lines.append("\n(No NESA / TSR material retrieved for this question. If you "
                     "cannot ground the answer, state plainly that the provided "
                     "course material does not cover it.)")

    lines.append("\n=== OUTPUT LANGUAGE ===")
    lines.append(f"Write the answer and the note in {lang_name}. Keep official "
                 "syllabus terms, module names and product names in their "
                 "original form.")

    lines.append("\nReturn ONLY the JSON object.")
    return system, "\n\n".join(lines)


# ----------------------------------------------------------------- normalisation

def _normalize_questions(data: dict, count: int) -> list:
    """Validate/coerce raw model JSON into the question list contract.

    Questions without text or with an unusable marks value are dropped; an
    output with no usable question raises ValueError, which lets
    generate_practice retry once with a stricter instruction.
    """
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")
    raw = data.get("questions")
    if not isinstance(raw, list):
        raise ValueError("model output has no questions list")

    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        text = str(item.get("question", "")).strip()
        if not text:
            continue
        try:
            marks = int(float(str(item.get("marks"))))
        except (TypeError, ValueError):
            continue  # a question without a mark value is not usable
        marks = max(MARKS_MIN, min(MARKS_MAX, marks))

        criteria = item.get("criteria")
        if isinstance(criteria, str):
            criteria = criteria.splitlines()
        criteria = [str(c).strip() for c in (criteria or []) if str(c).strip()]

        hint = str(item.get("hint", "")).strip()[:HINT_MAX_CHARS]
        out.append({"question": text, "marks": marks,
                    "criteria": criteria, "hint": hint})

    if not out:
        raise ValueError("model output has no usable questions")
    return out[:count]


def _normalize_answer(data: dict) -> dict:
    """Validate/coerce the model JSON into {answer, note}."""
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")
    answer = str(data.get("answer", "")).strip()
    if not answer:
        raise ValueError("model output has no answer field")
    note = str(data.get("note", "")).strip()[:NOTE_MAX_CHARS]
    return {"answer": answer, "note": note}


# ----------------------------------------------------------------- generation

def generate_practice(
    focus_dot_points: list | None = None,
    weak_areas: list | None = None,
    year: str = "Year 11",
    count: int = COUNT_DEFAULT,
    lang: str = "en",
    retrieved_docs: list | None = None,
) -> dict:
    """Generate targeted practice questions for one student.

    At least one of focus_dot_points / weak_areas is required (the UI passes
    the ticked dot points; a caller holding a tracker profile may pass
    weak_areas instead).

    Args:
        focus_dot_points: syllabus dot point texts to target (strings or
                          {code, text} dicts).
        weak_areas:       weak-area descriptions (e.g. from agents.tracker).
        year:             "Year 11" / "Year 12".
        count:            number of questions (clamped to 1..5).
        lang:             "en" / "zh" output language.
        retrieved_docs:   pre-fetched RAG hits (tests / callers that already
                          hold context). None triggers retrieval; [] means
                          "no documents".

    Returns:
        {"questions": [{"question", "marks", "criteria", "hint"}, ...],
         "focus": [str, ...]}

    Raises:
        ValueError:   no syllabus dot points AND no weak areas supplied.
        RuntimeError: LLM call failed or produced no usable JSON after retry.
    """
    dots = _clean_items(focus_dot_points)
    weak = _clean_items(weak_areas)
    if not dots and not weak:
        raise ValueError(
            "[student_coach] at least one focus dot point or weak area is required"
        )

    try:
        n = int(count)
    except (TypeError, ValueError):
        n = COUNT_DEFAULT
    n = max(COUNT_MIN, min(COUNT_MAX, n))

    year = str(year or "Year 11").strip() or "Year 11"
    if lang not in LANG_NAME:
        lang = "en"
    focus = _clean_items(list(dots) + list(weak))

    if retrieved_docs is None:
        query = (f"HSC Enterprise Computing {year} " + " ".join(focus))[:1000].strip()
        retrieved_docs = retrieve_context(query, k=RAG_K)
    docs = retrieved_docs or []

    system, user = build_practice_prompt(dots, weak, year, n, lang, docs)

    attempts = [
        (0.6, ""),
        (0.3, "\n\nIMPORTANT: your previous reply was not valid JSON or was "
              "missing usable questions. Reply with ONLY one complete JSON "
              "object, nothing else."),
    ]
    last_err = None
    for temp, extra in attempts:
        try:
            raw = complete(system, user + extra, temperature=float(temp),
                           max_tokens=3000)
            data = extract_json_block(raw)
            questions = _normalize_questions(data, n)
            return {"questions": questions, "focus": focus}
        except Exception as exc:  # noqa: BLE001 - parse/validation blip -> one retry
            last_err = exc

    raise RuntimeError(
        f"[student_coach.generate_practice] failed for year={year} "
        f"focus={focus[:2]!r}: {last_err}"
    )


def answer_question(
    student_question: str,
    context_note: str = "",
    year: str = "Year 11",
    lang: str = "en",
    retrieved_docs: list | None = None,
) -> dict:
    """Answer one student question from the NESA / TSR material (repository of truth).

    Args:
        student_question: the student's question (empty raises ValueError).
        context_note:     optional context, e.g. "I just got Q4 wrong".
        year:             "Year 11" / "Year 12".
        lang:             "en" / "zh" output language.
        retrieved_docs:   pre-fetched RAG hits. None triggers retrieval;
                          [] means "no documents" (the answer must then admit
                          what the material does not cover).

    Returns:
        {"answer": str, "sources": [str], "note": str}

    Raises:
        ValueError:   the question is empty.
        RuntimeError: LLM call failed or produced no usable JSON after retry.
    """
    question = str(student_question or "").strip()
    if not question:
        raise ValueError("[student_coach] student_question must not be empty")

    year = str(year or "Year 11").strip() or "Year 11"
    if lang not in LANG_NAME:
        lang = "en"

    if retrieved_docs is None:
        retrieved_docs = retrieve_context(question, k=RAG_K)
    docs = retrieved_docs or []

    system, user = build_answer_prompt(question, context_note, year, lang, docs)

    attempts = [
        (0.3, ""),
        (0.15, "\n\nIMPORTANT: your previous reply was not valid JSON or was "
               "missing the required answer field. Reply with ONLY one complete "
               "JSON object, nothing else."),
    ]
    last_err = None
    for temp, extra in attempts:
        try:
            raw = complete(system, user + extra, temperature=float(temp),
                           max_tokens=2500)
            data = extract_json_block(raw)
            out = _normalize_answer(data)
            return {"answer": out["answer"],
                    "sources": _doc_sources(docs),
                    "note": out["note"]}
        except Exception as exc:  # noqa: BLE001 - parse/validation blip -> one retry
            last_err = exc

    raise RuntimeError(f"[student_coach.answer_question] failed: {last_err}")


if __name__ == "__main__":  # quick manual check (requires a real API key)
    import json as _json
    _out = generate_practice(
        focus_dot_points=[
            "Explain how the user interface (UI) impacts on the user experience (UX)"
        ],
        year="Year 11", count=2,
    )
    print(_json.dumps(_out, ensure_ascii=False, indent=2))
