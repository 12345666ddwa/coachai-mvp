#!/usr/bin/env python3
"""
CoachAI Lesson Planner Agent (Phase 4) — syllabus-grounded lesson generation.

Input:
    * syllabus dot points ticked by the teacher (the lesson must cover them),
    * optional teacher reference material (slides / textbook extract / past
      materials) that acts as the content baseline,
    * year, module (focus area) and lesson duration.

Grounding: the NESA TSR support-material collection (RAG, k=4) plus the
ticked dot points themselves.

Output: a structured lesson plan dict

    {
        "title": str,
        "year": str, "duration_min": int, "focus_area": str,
        "objectives": [str, ...],          # 3-5 assessable objectives
        "flow": [{"time": "0–10", "activity": str, "detail": str}, ...],
        "assessment": str,                 # exit-ticket style check
        "alignment": [str, ...],           # always the ticked dot points
        "generated_with": {"reference_len": int, "rag_used": bool},
    }

All LLM calls go through agents.models.complete() (project-wide convention).

Typical usage:

    from agents.lesson_planner import generate_lesson_plan
    plan = generate_lesson_plan(["Describe the features of ..."],
                                reference_text="Week 3 slides ...",
                                year="Year 12", duration_min=60,
                                focus_area="Data science")
"""

from __future__ import annotations

import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents.marker import extract_json_block  # noqa: E402
from agents.models import complete  # noqa: E402

SYLLABUS_PATH = os.path.join(_ROOT, "data", "syllabus.json")
RAG_K = 4
REF_LIMIT = 6000      # max characters of teacher reference material in the prompt
DOC_LIMIT = 1200      # max characters per retrieved TSR chunk
FLOW_LIMIT = 6        # keep 4-6 flow segments (hard cap 6)
MIN_OBJECTIVES = 3
MAX_OBJECTIVES = 5

LANG_NAME = {"en": "English", "zh": "Simplified Chinese (简体中文)"}

SYSTEM_ROLE = (
    "You are an experienced HSC Enterprise Computing teacher in New South Wales, "
    "Australia, who plans single, classroom-ready lessons for Year 11 and Year 12. "
    "You design plans that are faithful to the NESA Enterprise Computing syllabus: "
    "every activity exists to serve the dot points the teacher selected, and the "
    "terminology you use matches the syllabus and any reference material provided. "
    "Your learning objectives are observable and assessable (they open with a verb "
    "such as explain, compare, model, construct, evaluate) and describe what "
    "students will be able to do by the end of the lesson, never vague aims like "
    "'understand' or 'be aware of'. Your lesson flow is a realistic sequence for "
    "the stated duration, starting with a short hook or review, moving through "
    "teacher-led and student-led phases, and closing with a check for understanding. "
    "You NEVER invent NESA content that is not implied by the dot points, the "
    "reference material or the retrieved context."
)


# ----------------------------------------------------------------- syllabus helpers

def load_syllabus(path: str = SYLLABUS_PATH) -> dict:
    """Load data/syllabus.json (Year 11 / Year 12 modules + all_outcomes)."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def list_modules(syllabus: dict, year: str) -> list:
    """Focus-area names for one year, in syllabus order. [] when year unknown."""
    entry = (syllabus or {}).get(year) or {}
    out = []
    for mod in entry.get("modules") or []:
        name = str(mod.get("focus_area", "")).strip()
        if name:
            out.append(name)
    return out


def module_dot_points(syllabus: dict, year: str, focus_area: str) -> list:
    """Dot points of one module as [{code, text, group}], syllabus order kept."""
    entry = (syllabus or {}).get(year) or {}
    target = str(focus_area or "").strip()
    out = []
    for mod in entry.get("modules") or []:
        if str(mod.get("focus_area", "")).strip() != target:
            continue
        for cg in mod.get("content_groups") or []:
            group = str(cg.get("title", "")).strip()
            for dp in cg.get("dot_points") or []:
                text = str(dp.get("text", "")).strip()
                if not text:
                    continue
                out.append({"code": str(dp.get("code", "")).strip(),
                            "text": text, "group": group})
    return out


def dot_point_texts(syllabus: dict, year: str, focus_area: str) -> list:
    """Just the dot point texts of one module (what the UI checkbox values use)."""
    return [d["text"] for d in module_dot_points(syllabus, year, focus_area)]


# ----------------------------------------------------------------- language / prompt

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")


def infer_lang(*texts, threshold: int = 8) -> str:
    """'zh' when CJK characters dominate the supplied text, else 'en'.

    Dot points and reference material decide the lesson language: Chinese
    material in, Chinese plan out; English material in, English plan out.
    """
    blob = " ".join(str(t or "") for t in texts)
    cjk = len(_CJK_RE.findall(blob))
    latin_words = len(_LATIN_WORD_RE.findall(blob))
    return "zh" if (cjk >= threshold and cjk >= latin_words) else "en"


def _doc_text(doc: dict, limit: int = DOC_LIMIT) -> str:
    """Compact a retrieved document for prompt context."""
    text = str(doc.get("text", "")).strip().replace("\r", "")
    return text[:limit] + ("…" if len(text) > limit else "")


def retrieve_context(query: str, k: int = RAG_K) -> list:
    """RAG over the NESA TSR collection; [] when retrieval is unavailable.

    Retrieval must never kill lesson generation (same policy as mark_graph).
    """
    try:
        from rag.retriever import search
        return search(query, k=k) or []
    except Exception as exc:  # noqa: BLE001
        print(f"[lesson_planner] RAG retrieval unavailable, continuing without docs: {exc}")
        return []


def _clean_dot_points(items) -> list:
    """Normalise the ticked dot points into a deduped list of non-empty strings."""
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


def build_lesson_prompt(
    selected_dot_points: list,
    reference_text: str,
    year: str,
    duration_min: int,
    focus_area: str,
    lang: str,
    retrieved_docs: list,
) -> tuple:
    """Assemble (system, user) prompt pair for the lesson planner agent."""
    lang_name = LANG_NAME.get(lang, LANG_NAME["en"])
    system = SYSTEM_ROLE + (
        "\n\nOutput contract: reply with a single JSON object of the form\n"
        '{"title": "<lesson title>", "objectives": ["<verb-led objective>", "..."], '
        '"flow": [{"time": "0–10", "activity": "<phase name>", '
        '"detail": "<what teacher and students actually do>"}], '
        '"assessment": "<exit-ticket / check-for-understanding design>", '
        '"alignment": ["<dot point covered>", "..."]}\n'
        f"Rules: give {MIN_OBJECTIVES}-{MAX_OBJECTIVES} objectives; give 4-6 flow "
        f"segments whose time labels together cover the full {duration_min} "
        "minutes; every flow entry needs both an activity and a concrete detail "
        "line; the assessment must be observable within the lesson (an exit "
        "ticket, quick quiz, or similar), not homework. Do not add fields."
    )

    lines = []
    lines.append("=== LESSON REQUEST ===")
    lines.append(f"Year: {year}")
    lines.append(f"Focus area (syllabus module): {focus_area or '(not specified)'}")
    lines.append(f"Lesson duration: {duration_min} minutes")
    lines.append("\nSyllabus dot points selected by the teacher "
                 "(the lesson MUST cover every one of them):")
    for i, dp in enumerate(selected_dot_points, 1):
        lines.append(f"{i}. {dp}")

    ref = (reference_text or "").strip()
    if ref:
        lines.append("\n=== REFERENCE MATERIAL (teacher-provided; treat it as the content "
                     "baseline — align terminology, examples, scope and sequence with it; "
                     "do not contradict it) ===")
        lines.append(ref[:REF_LIMIT] + ("…" if len(ref) > REF_LIMIT else ""))
    else:
        lines.append("\n(No reference material provided — base the content on the dot "
                     "points above and the retrieved material below.)")

    docs = retrieved_docs or []
    if docs:
        lines.append("\n=== RETRIEVED NESA / TSR CONTEXT (support material; use it for "
                     "accurate terminology and depth, do not treat it as compulsory "
                     "content) ===")
        for i, d in enumerate(docs[:RAG_K], 1):
            src = d.get("source", "?") if isinstance(d, dict) else "?"
            lines.append(f"[ref {i} | source: {src}] {_doc_text(d)}")
    else:
        lines.append("\n(No TSR context retrieved; rely on the syllabus dot points and "
                     "your own expertise.)")

    lines.append("\n=== OUTPUT LANGUAGE ===")
    lines.append(f"Write every human-readable string (\u201ctitle\u201d, objectives, "
                 f"flow activity and detail, assessment, alignment) in {lang_name}. "
                 "Keep official syllabus terms, module names and product names in "
                 "their original form.")

    lines.append("\nProduce the lesson plan as a DRAFT for the teacher to edit before "
                 "use. Return ONLY the JSON object.")
    return system, "\n\n".join(lines)


# ----------------------------------------------------------------- normalisation

def _normalize_flow(flow) -> list:
    """Coerce model flow entries into [{'time','activity','detail'}] (max 6)."""
    out = []
    if not isinstance(flow, list):
        return out
    for seg in flow:
        if isinstance(seg, dict):
            time = str(seg.get("time", "")).strip()
            activity = str(seg.get("activity", "")).strip()
            detail = str(seg.get("detail", "")).strip()
        elif isinstance(seg, str):
            time, activity, detail = "", seg.strip(), ""
        else:
            continue
        if not (activity or detail):
            continue
        out.append({"time": time or "?", "activity": activity or detail, "detail": detail})
    return out[:FLOW_LIMIT]


def _normalize_plan(
    data: dict,
    dot_points: list,
    year: str,
    duration_min: int,
    focus_area: str,
    reference_text: str,
    rag_used: bool,
) -> dict:
    """Validate/coerce raw model JSON into the lesson plan contract.

    Raises ValueError when the output is too thin to be a lesson plan, which
    lets generate_lesson_plan retry once with a stricter instruction.
    """
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")

    title = str(data.get("title", "")).strip()
    if not title:
        raise ValueError("model output has no lesson title")

    objectives = [str(x).strip() for x in (data.get("objectives") or []) if str(x).strip()]
    if not objectives:
        raise ValueError("model output has no learning objectives")

    flow = _normalize_flow(data.get("flow"))
    if not flow:
        raise ValueError("model output has no lesson flow")

    return {
        "title": title,
        "year": year,
        "duration_min": int(duration_min),
        "focus_area": str(focus_area or "").strip(),
        "objectives": objectives[:MAX_OBJECTIVES],
        "flow": flow,
        "assessment": str(data.get("assessment", "")).strip()
                      or "(no assessment point provided)",
        # Contract: alignment is exactly what the teacher ticked, so the plan
        # can never silently drop a selected dot point.
        "alignment": list(dot_points),
        "generated_with": {"reference_len": len(reference_text or ""),
                           "rag_used": bool(rag_used)},
    }


# ----------------------------------------------------------------- generation

def generate_lesson_plan(
    selected_dot_points: list,
    reference_text: str = "",
    year: str = "Year 11",
    duration_min: int = 60,
    focus_area: str = "",
    lang: str | None = None,
    retrieved_docs: list | None = None,
) -> dict:
    """Generate one structured lesson plan (see module docstring for the shape).

    Args:
        selected_dot_points: syllabus dot point texts ticked by the teacher.
                             At least one is required.
        reference_text:      optional teacher material; the content baseline.
        year:                "Year 11" / "Year 12".
        duration_min:        lesson length in minutes (clamped to 20..180).
        focus_area:          module name, e.g. "Data science".
        lang:                "en"/"zh" output language; None = infer from
                             reference_text + dot points.
        retrieved_docs:      pre-fetched RAG hits (mainly for tests / callers
                             that already hold context). None triggers
                             retrieval; [] means "no documents".

    Raises:
        ValueError: no dot points selected.
        RuntimeError: LLM call failed or produced no usable plan after retry.
    """
    dot_points = _clean_dot_points(selected_dot_points)
    if not dot_points:
        raise ValueError("[lesson_planner] at least one syllabus dot point is required")

    year = str(year or "Year 11").strip() or "Year 11"
    try:
        duration = int(duration_min)
    except (TypeError, ValueError):
        duration = 60
    duration = max(20, min(180, duration))
    focus_area = str(focus_area or "").strip()
    reference_text = (reference_text or "").strip()

    if lang not in LANG_NAME:
        lang = infer_lang(reference_text, " ".join(dot_points))

    if retrieved_docs is None:
        query = (focus_area + " " + " ".join(dot_points))[:1000].strip()
        retrieved_docs = retrieve_context(query, k=RAG_K)
    docs = retrieved_docs or []

    system, user = build_lesson_prompt(
        dot_points, reference_text, year, duration, focus_area, lang, docs
    )

    attempts = [
        (0.4, ""),
        (0.2, "\n\nIMPORTANT: your previous reply was not valid JSON or was missing "
              "required sections. Reply with ONLY a complete JSON object, nothing else."),
    ]
    last_err = None
    for temp, extra in attempts:
        try:
            raw = complete(system, user + extra, temperature=float(temp), max_tokens=3000)
            data = extract_json_block(raw)
            return _normalize_plan(
                data, dot_points, year, duration, focus_area, reference_text, bool(docs)
            )
        except Exception as exc:  # noqa: BLE001 — parse/validation blip -> one retry
            last_err = exc

    raise RuntimeError(
        f"[lesson_planner.generate_lesson_plan] failed for year={year} "
        f"focus_area={focus_area!r}: {last_err}"
    )


if __name__ == "__main__":  # quick manual check (requires a real API key)
    import pprint
    syl = load_syllabus()
    mods = list_modules(syl, "Year 12")
    dps = dot_point_texts(syl, "Year 12", mods[0])
    out = generate_lesson_plan(dps[:2], year="Year 12", focus_area=mods[0])
    pprint.pprint(out)
