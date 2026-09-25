#!/usr/bin/env python3
"""
CoachAI Transcript Analyzer (Phase 6b): lesson recording review.

Two services:

transcribe_audio(audio_path) -> dict
    Local speech-to-text with faster-whisper (small model, CPU, int8).
    Returns {"transcript": str, "segments": int, "language": str, "duration_s": float}

analyze_lesson(transcript_text, year, focus_area, expected_dot_points, lang) -> dict
    The transcript is handed to the LLM together with the expected syllabus
    dot points (default: every dot point of the year / focus area). For each
    dot point the LLM judges whether the lesson really covered it and quotes a
    verbatim transcript fragment as evidence; it also reports teaching
    strengths, thin or missing content, and next-lesson recommendations.

    Returns:
    {
        "lesson_summary": str,
        "strengths": [str, ...],
        "missed": [str, ...],
        "coverage": [{"dot_point": str, "covered": bool, "evidence": str}, ...],
        "recommendations": [str, ...],
    }

All LLM calls go through agents.models.complete() (project-wide convention).

Typical usage:

    from tools.transcript_analyzer import transcribe_audio, analyze_lesson
    tr = transcribe_audio("lesson.m4a")
    review = analyze_lesson(tr["transcript"], year="Year 11",
                            focus_area="Principles of cybersecurity")
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents.marker import extract_json_block  # noqa: E402
from agents.models import complete  # noqa: E402

# Whisper settings (same pipeline already used by transcribe_meeting.py).
WHISPER_MODEL_SIZE = "small"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

MAX_TRANSCRIPT_CHARS = 12000   # transcript is truncated to this length in the prompt
MAX_RECOMMENDATIONS = 5        # keep 3-5 concrete recommendations
MAX_ITEMS = 6                  # strengths / missed items cap
MIN_MATCH_CHARS = 12           # shortest key used for fuzzy dot point matching

LANG_NAME = {"en": "English", "zh": "Simplified Chinese (简体中文)"}

SYSTEM_ROLE = (
    "You are an experienced HSC Enterprise Computing teacher in New South Wales, "
    "Australia, acting as a peer reviewer of one recorded lesson. You receive an "
    "auto-transcribed lesson transcript and a numbered list of syllabus dot points "
    "the lesson was expected to cover, and you produce a measured, evidence-based "
    "review for the teacher. "
    "Coverage judgement rules: judge each dot point ONLY against what the transcript "
    "actually shows the teacher and students doing or saying. Set covered to true "
    "only when the lesson really teaches or substantively discusses that content, "
    "and quote a short fragment copied verbatim from the transcript as evidence. "
    "Never quote text that is not in the transcript. When you are unsure, or when "
    "the content is only named without being explained, set covered to false and "
    "state plainly what is missing. "
    "You also identify teaching strengths that are visible in the transcript (a "
    "clear worked example, effective student questioning, a check for understanding) "
    "and thin spots (a concept named but not unpacked, a missing example, a rushed "
    "close). You never invent events, student names or content that are absent from "
    "the transcript. You return ONLY a JSON object, no markdown, no prose."
)


# ----------------------------------------------------------------- transcript

def transcribe_audio(audio_path: str) -> dict:
    """Transcribe a lesson recording with faster-whisper (small, CPU, int8).

    The import is done inline so a missing dependency surfaces as a friendly
    RuntimeError instead of breaking this module on import.

    Args:
        audio_path: path to an audio file (mp3 / m4a / wav and other formats
                    faster-whisper can decode).

    Returns:
        {"transcript": str, "segments": int, "language": str, "duration_s": float}

    Raises:
        FileNotFoundError: the path is empty or does not point to a file.
        RuntimeError:      faster-whisper is not installed, or transcription
                           itself failed.
    """
    path = str(audio_path or "").strip()
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(
            f"[transcript_analyzer] audio file not found: {path or '(empty path)'}"
        )

    try:
        from faster_whisper import WhisperModel  # noqa: PLC0415 (optional dependency)
    except ImportError as exc:
        raise RuntimeError(
            "[transcript_analyzer] faster-whisper is not installed. "
            "Install it with: pip install faster-whisper"
        ) from exc

    try:
        model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE,
                             compute_type=WHISPER_COMPUTE_TYPE)
        segments, info = model.transcribe(path, vad_filter=True, beam_size=5)
        parts, count = [], 0
        for seg in segments:  # generator: decoding happens while iterating
            count += 1
            text = str(getattr(seg, "text", "") or "").strip()
            if text:
                parts.append(text)
    except Exception as exc:  # noqa: BLE001 (model load / decode failure)
        raise RuntimeError(
            f"[transcript_analyzer] transcription failed for {path!r}: {exc}"
        ) from exc

    return {
        "transcript": "\n".join(parts).strip(),
        "segments": count,
        "language": str(getattr(info, "language", "") or ""),
        "duration_s": round(float(getattr(info, "duration", 0.0) or 0.0), 1),
    }


# ----------------------------------------------------------------- syllabus

def default_dot_points(year: str, focus_area: str = "") -> list:
    """All syllabus dot point texts for a year (+ optional focus area).

    An empty focus area means every module of that year. Returns [] when the
    syllabus cannot be loaded (the caller decides how to react).
    """
    try:
        from agents.lesson_planner import (  # noqa: PLC0415
            list_modules,
            load_syllabus,
            module_dot_points,
        )
        syllabus = load_syllabus()
        area = str(focus_area or "").strip()
        areas = [area] if area else list_modules(syllabus, year)
        out = []
        for name in areas:
            out.extend(d["text"] for d in module_dot_points(syllabus, year, name))
        return out
    except Exception as exc:  # noqa: BLE001
        print(f"[transcript_analyzer] syllabus load failed: {exc}")
        return []


# ----------------------------------------------------------------- helpers

def _clean_items(items) -> list:
    """Normalise a raw list into deduped non-empty strings (dicts use 'text').

    Non-list input (a bare string, None, a number) comes back as [].
    """
    if not isinstance(items, (list, tuple)):
        return []
    out, seen = [], set()
    for it in items or []:
        text = str(it.get("text", "")).strip() if isinstance(it, dict) else str(it).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _norm_key(text: str) -> str:
    """Whitespace/case-insensitive key for matching dot point texts."""
    return " ".join(str(text or "").casefold().split())


def _as_bool(value) -> bool:
    """Coerce a model 'covered' value; anything uncertain counts as not covered."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        token = value.strip().casefold()
        if token in ("true", "yes", "covered", "1"):
            return True
        return False
    if isinstance(value, (int, float)):
        return value == 1
    return False


def _prepare_transcript(text: str) -> tuple:
    """Truncate an over-long transcript; returns (text, was_truncated)."""
    if len(text) <= MAX_TRANSCRIPT_CHARS:
        return text, False
    return text[:MAX_TRANSCRIPT_CHARS], True


# ----------------------------------------------------------------- prompt assembly

def build_analysis_prompt(
    transcript_text: str,
    dot_points: list,
    year: str = "Year 11",
    focus_area: str = "",
    lang: str = "en",
) -> tuple:
    """Assemble (system, user) prompt pair for the lesson review agent.

    Args:
        transcript_text: the lesson transcript (truncated here when too long).
        dot_points:      expected syllabus dot point texts, judged one by one.
        year:            "Year 11" / "Year 12".
        focus_area:      module the lesson belongs to ("" = whole year).
        lang:            "en" / "zh" output language.
    """
    lang_name = LANG_NAME.get(lang, LANG_NAME["en"])
    system = SYSTEM_ROLE + (
        "\n\nOutput contract: reply with a single JSON object of the form\n"
        '{"lesson_summary": "<2 to 3 sentence overview of what this lesson was about>", '
        '"strengths": ["<specific teaching strength visible in the transcript>"], '
        '"missed": ["<content that was omitted or explained too thinly>"], '
        '"coverage": [{"dot_point": "<text copied verbatim from the numbered list>", '
        '"covered": true|false, "evidence": "<verbatim transcript quote, or why this '
        'content is not covered>"}], '
        '"recommendations": ["<concrete action for the next lesson>"]}\n'
        "Rules: the coverage list must hold exactly one entry for EVERY numbered "
        "dot point, in the same order, with the dot point text copied verbatim; "
        "covered is the boolean true or false; when covered is true the evidence "
        "must quote the transcript (never the syllabus); strengths and missed hold "
        "1 to 6 one-sentence items each; recommendations hold 3 to 5 concrete "
        "actions. Plain text only: no markdown, no emoji, no extra fields."
    )

    body, truncated = _prepare_transcript(str(transcript_text or "").strip())

    lines = []
    lines.append("=== LESSON TRANSCRIPT (auto-transcribed recording) ===")
    lines.append(body if body else "(empty transcript)")
    if truncated:
        lines.append(
            f"(Note: the recording is longer than {MAX_TRANSCRIPT_CHARS} "
            "characters, so the transcript was truncated to the first "
            f"{MAX_TRANSCRIPT_CHARS} characters.)"
        )

    lines.append("\n=== SYLLABUS DOT POINTS TO CHECK (one coverage entry per point, "
                 "in this order) ===")
    dots = list(dot_points or [])
    if dots:
        for i, text in enumerate(dots, 1):
            lines.append(f"{i}. {text}")
    else:
        lines.append("(no dot points supplied)")

    context = [f"Year: {year}"]
    area = str(focus_area or "").strip()
    context.append(f"Focus area: {area}" if area else
                   "Focus area: (not specified; the dot point list covers the whole year)")
    lines.append("\n=== COURSE CONTEXT ===")
    lines.extend(context)

    lines.append("\n=== OUTPUT LANGUAGE ===")
    lines.append(f"Write lesson_summary, strengths, missed, recommendations and every "
                 f"evidence string in {lang_name}. Keep official syllabus terms, "
                 "module names and product names in their original form.")

    lines.append("\nProduce the lesson review as a DRAFT the teacher will confirm. "
                 "Return ONLY the JSON object.")
    return system, "\n\n".join(lines)


# ----------------------------------------------------------------- analysis

def _match_coverage(raw_coverage: list, dot_points: list) -> list:
    """Align the model coverage entries with the expected dot points.

    Exact (case/whitespace-insensitive) matches win; a containment match is
    accepted when the shorter side is at least MIN_MATCH_CHARS long. Dot
    points the model did not judge come back as not covered, and entries for
    dot points that were never requested are dropped.
    """
    entries = []
    for item in raw_coverage:
        if not isinstance(item, dict):
            continue
        key = _norm_key(str(item.get("dot_point") or ""))
        if not key:
            continue
        entries.append({"key": key,
                        "covered": _as_bool(item.get("covered")),
                        "evidence": str(item.get("evidence", "")).strip()})

    used = set()
    coverage = []
    for dp in dot_points:
        key = _norm_key(dp)
        hit = None
        for i, entry in enumerate(entries):
            if i in used:
                continue
            if entry["key"] == key:
                hit = i
                break
            shorter = min(len(key), len(entry["key"]))
            if shorter >= MIN_MATCH_CHARS and (
                    key in entry["key"] or entry["key"] in key):
                hit = i
                break
        if hit is None:
            coverage.append({"dot_point": dp, "covered": False,
                             "evidence": "(not judged by the model)"})
        else:
            used.add(hit)
            coverage.append({"dot_point": dp,
                             "covered": entries[hit]["covered"],
                             "evidence": entries[hit]["evidence"]})
    return coverage


def _normalize_analysis(data: dict, dot_points: list) -> dict:
    """Validate/coerce raw model JSON into the review contract."""
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")
    raw_coverage = data.get("coverage")
    if not isinstance(raw_coverage, list) or not raw_coverage:
        raise ValueError("model output has no coverage list")

    summary = str(data.get("lesson_summary", "")).strip() \
        or "(no lesson summary returned)"
    recommendations = _clean_items(data.get("recommendations"))[:MAX_RECOMMENDATIONS]
    return {
        "lesson_summary": summary,
        "strengths": _clean_items(data.get("strengths"))[:MAX_ITEMS],
        "missed": _clean_items(data.get("missed"))[:MAX_ITEMS],
        "coverage": _match_coverage(raw_coverage, list(dot_points or [])),
        "recommendations": recommendations,
    }


def analyze_lesson(
    transcript_text: str,
    year: str = "Year 11",
    focus_area: str = "",
    expected_dot_points: list | None = None,
    lang: str = "en",
) -> dict:
    """Analyse a lesson transcript against the syllabus (LLM judgement only).

    Coverage is decided by the model, one dot point at a time, with a verbatim
    transcript quote as evidence; when the model is unsure the dot point stays
    not covered. This function never guesses coverage locally.

    Args:
        transcript_text:    the lesson transcript (empty raises ValueError).
        year:               "Year 11" / "Year 12".
        focus_area:         module filter ("" = every module of the year).
        expected_dot_points: dot point texts to check (None or [] = resolve
                            from data/syllabus.json via default_dot_points).
        lang:               "en" / "zh" output language.

    Returns:
        {"lesson_summary", "strengths", "missed", "coverage", "recommendations"}

    Raises:
        ValueError:   transcript empty, or no expected dot points resolvable.
        RuntimeError: LLM call failed or produced no usable JSON after retry.
    """
    text = str(transcript_text or "").strip()
    if not text:
        raise ValueError("[transcript_analyzer] transcript_text must not be empty")

    year = str(year or "Year 11").strip() or "Year 11"
    focus_area = str(focus_area or "").strip()
    if lang not in LANG_NAME:
        lang = "en"

    dots = _clean_items(expected_dot_points)
    if not dots:
        dots = _clean_items(default_dot_points(year, focus_area))
    if not dots:
        raise ValueError(
            f"[transcript_analyzer] no syllabus dot points found for "
            f"{year!r} / {focus_area!r}"
        )

    system, user = build_analysis_prompt(text, dots, year, focus_area, lang)

    attempts = [
        (0.3, ""),
        (0.15, "\n\nIMPORTANT: your previous reply was not valid JSON or was "
               "missing the coverage list. Reply with ONLY one complete JSON "
               "object, nothing else."),
    ]
    last_err = None
    for temp, extra in attempts:
        try:
            raw = complete(system, user + extra, temperature=float(temp),
                           max_tokens=4000)
            data = extract_json_block(raw)
            return _normalize_analysis(data, dots)
        except Exception as exc:  # noqa: BLE001 - parse/validation blip -> one retry
            last_err = exc

    raise RuntimeError(
        f"[transcript_analyzer.analyze_lesson] failed for year={year} "
        f"({len(dots)} dot points): {last_err}"
    )


if __name__ == "__main__":  # manual check (analysis requires a real API key)
    import json as _json

    if len(sys.argv) > 1:  # python3 tools/transcript_analyzer.py recording.m4a
        _tr = transcribe_audio(sys.argv[1])
        print(f"transcribed: {_tr['segments']} segments | "
              f"{len(_tr['transcript'])} chars | language={_tr['language']} | "
              f"{_tr['duration_s']}s")
        _text = _tr["transcript"]
    else:
        _text = ("Today we looked at design thinking and how it feeds into the user "
                 "experience. Remember the five stages: empathise, define, ideate, "
                 "prototype and test. Let us apply them to a booking page scenario...")

    _out = analyze_lesson(
        _text,
        year="Year 11",
        expected_dot_points=[
            "Apply design thinking to develop a front-end, web-based interactive "
            "media system incorporating UX and UI principles"
        ],
    )
    print(_json.dumps(_out, ensure_ascii=False, indent=2))
