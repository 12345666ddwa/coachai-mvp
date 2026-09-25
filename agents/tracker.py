#!/usr/bin/env python3
"""
CoachAI Student Tracker Agent (Phase 5): progress profiles from marking history.

Design: all arithmetic is done in plain Python (compute_stats) and the numbers
are handed to the LLM ready-made. The model only writes prose (the
current_level description and the recommendations) and is explicitly told not
to recalculate anything. Trend, weak areas and evidence bullets are
deterministic so the same history always yields the same profile skeleton.

Output (analyze_student):

    {
        "student_id": int,
        "student_name": str,
        "current_level": str,        # LLM-written 2-3 sentence description
        "trend": "improving" | "stable" | "declining" | "volatile" | "insufficient_data",
        "trend_evidence": [str, ...],  # deterministic, built from the numbers
        "weak_areas": [str, ...],      # deterministic, per-question below threshold
        "recommendations": [str, ...], # LLM-written, grounded in the numbers
        "has_data": bool,
        "total_submissions": int,
        "avg_score_rate": float | None,
    }

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

# ------------------------------------------------------------------ trend tuning
TREND_SLOPE = 0.04        # score-rate change per attempt that counts as a direction
VOLATILE_SPREAD = 0.25    # max-min spread that counts as a swing
VOLATILE_FLIPS = 2        # direction reversals among consecutive deltas
WEAK_THRESHOLD = 0.60     # per-question average below this = weak area
WINDOW = 5                # recent attempts used for the trend judgement
RECO_LIMIT = 5
LEVEL_MAX_CHARS = 1200

TRENDS = ("improving", "stable", "declining", "volatile", "insufficient_data")

SYSTEM_ROLE = (
    "You are an experienced HSC Enterprise Computing teacher in New South Wales, "
    "Australia, reviewing a student's progress profile to plan the next steps in "
    "your teaching. You are given PRE-COMPUTED statistics: trust them exactly "
    "and never recalculate, re-derive or contradict the numbers. "
    "Your current_level description is written for the teacher (not the student): "
    "2 to 3 sentences that summarise where the student is now, using the trend "
    "and the per-question averages as the evidence base. "
    "Your recommendations are 3 to 5 concrete, actionable teaching or study "
    "actions tied to the weak areas and the trend, naming the topic or question "
    "each recommendation targets where possible. Never invent data that is not "
    "in the statistics you were given."
)


# ------------------------------------------------------------------ pure statistics

def _ls_slope(values: list) -> float:
    """Least-squares slope of values vs. index (0 when undefined)."""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    num = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return num / den if den else 0.0


def detect_trend(rates: list) -> str:
    """Deterministic trend label for a chronological list of score rates (0..1).

    improving / stable / declining come from the least-squares slope over the
    recent window; volatile is a large spread whose direction keeps flipping
    (or a large spread with no overall direction); fewer than 2 points is
    reported as insufficient_data.
    """
    rates = [float(r) for r in rates]
    if len(rates) < 2:
        return "insufficient_data"

    spread = max(rates) - min(rates)
    deltas = [b - a for a, b in zip(rates, rates[1:])]
    flips = sum(1 for i in range(len(deltas) - 1)
                if deltas[i] * deltas[i + 1] < 0)
    slope = _ls_slope(rates)

    if flips >= VOLATILE_FLIPS and spread >= VOLATILE_SPREAD:
        return "volatile"
    if slope >= TREND_SLOPE:
        return "improving"
    if slope <= -TREND_SLOPE:
        return "declining"
    if spread >= VOLATILE_SPREAD:
        return "volatile"
    return "stable"


def _fmt_pct(rate) -> str:
    """0.6667 -> '67%'; None -> 'n/a'."""
    if rate is None:
        return "n/a"
    try:
        return f"{round(float(rate) * 100)}%"
    except (TypeError, ValueError):
        return "n/a"


def compute_stats(history: list) -> dict:
    """Aggregate one student's submissions into a deterministic stats dict.

    Pure function (no db, no LLM). Only rows with both marks and max_marks
    count towards the score rates; other rows still count in total_submissions.
    """
    rates: list = []              # chronological per-attempt score rates
    by_question: dict = {}
    for sub in history or []:
        qid = str(sub.get("question_id", "?"))
        marks, max_marks = sub.get("marks_awarded"), sub.get("max_marks")
        bucket = by_question.setdefault(
            qid, {"question_id": qid, "attempts": 0, "max_marks": max_marks,
                  "rates": []})
        bucket["attempts"] += 1
        if max_marks:
            bucket["max_marks"] = max_marks
        if marks is not None and max_marks:
            rate = float(marks) / float(max_marks)
            rates.append(rate)
            bucket["rates"].append(rate)

    question_stats = []
    for qid in sorted(by_question):
        b = by_question[qid]
        n = len(b["rates"])
        question_stats.append({
            "question_id": qid,
            "attempts": b["attempts"],
            "max_marks": b["max_marks"],
            "avg_score_rate": round(sum(b["rates"]) / n, 4) if n else None,
        })

    window = rates[-WINDOW:]
    trend = detect_trend(window)
    avg_rate = round(sum(rates) / len(rates), 4) if rates else None

    weak_areas = [
        f"{q['question_id']}: {_fmt_pct(q['avg_score_rate'])} average over "
        f"{q['attempts']} attempt(s)"
        for q in question_stats
        if q["avg_score_rate"] is not None and q["avg_score_rate"] < WEAK_THRESHOLD
    ]

    evidence = []
    if rates:
        seq = " -> ".join(_fmt_pct(r) for r in window)
        evidence.append(f"Recent score rates (oldest to newest, up to {WINDOW}): {seq}.")
        change = window[-1] - window[0]
        evidence.append(
            f"Change across that window: {change:+.0%} "
            f"(first {_fmt_pct(window[0])} to latest {_fmt_pct(window[-1])})."
        )
        evidence.append(
            f"Average across {len(rates)} usable attempt(s): {_fmt_pct(avg_rate)} "
            f"(trend: {trend})."
        )
        if weak_areas:
            evidence.append(
                f"{len(weak_areas)} question(s) below the "
                f"{_fmt_pct(WEAK_THRESHOLD)} threshold."
            )

    return {
        "total_submissions": len(history or []),
        "usable_count": len(rates),
        "avg_score_rate": avg_rate,
        "score_rates": rates,
        "window_rates": window,
        "trend": trend,
        "trend_evidence": evidence,
        "by_question": question_stats,
        "weak_areas": weak_areas,
    }


# ------------------------------------------------------------------ prompt

def build_tracker_prompt(stats: dict) -> tuple:
    """Assemble (system, user) prompt pair for the tracker agent.

    `stats` is the compute_stats dict, optionally enriched with student_name /
    year / gender by analyze_student. Pure function, safe to unit test.
    """
    system = SYSTEM_ROLE + (
        "\n\nOutput contract: reply with a single JSON object of the form\n"
        '{"current_level": "<2-3 sentence description for the teacher>", '
        '"recommendations": ["<concrete action tied to the numbers>"]}\n'
        "Rules: 3 to 5 recommendations; each names the evidence it targets "
        "(question id, topic or trend); no markdown, no emoji, no extra fields."
    )

    name = str(stats.get("student_name") or "The student").strip()
    lines = []
    lines.append("=== STUDENT ===")
    lines.append(f"Name: {name}")
    if stats.get("year"):
        lines.append(f"Year: {stats.get('year')}")
    if stats.get("gender"):
        lines.append(f"Gender code: {stats.get('gender')}")

    lines.append("\n=== PRE-COMPUTED STATISTICS (do not recalculate) ===")
    lines.append(f"Submissions recorded: {stats.get('total_submissions', 0)}")
    lines.append(f"Usable attempts (with marks): {stats.get('usable_count', 0)}")
    lines.append(f"Average score rate: {_fmt_pct(stats.get('avg_score_rate'))}")
    lines.append(f"Trend (deterministic): {stats.get('trend')}")

    lines.append("\nTrend evidence already derived:")
    for e in stats.get("trend_evidence") or ["(none)"]:
        lines.append(f"- {e}")

    lines.append("\nPer-question averages:")
    q_lines = []
    for q in stats.get("by_question") or []:
        q_lines.append(
            f"- {q.get('question_id')}: {q.get('attempts')} attempt(s), "
            f"average {_fmt_pct(q.get('avg_score_rate'))} "
            f"(max {q.get('max_marks')} marks)"
        )
    lines.extend(q_lines or ["- (no per-question data)"])

    lines.append("\nWeak areas already identified (below "
                 f"{_fmt_pct(WEAK_THRESHOLD)} average):")
    for w in stats.get("weak_areas") or ["(none)"]:
        lines.append(f"- {w}")

    lines.append("\nWrite the progress profile for the teacher now: the "
                 "current_level description and the recommendations. Return "
                 "ONLY the JSON object.")
    return system, "\n\n".join(lines)


# ------------------------------------------------------------------ generation

def _empty_profile(student: dict, stats: dict) -> dict:
    """Safe profile for students without any usable marking records (no LLM)."""
    return {
        "student_id": student.get("id"),
        "student_name": str(student.get("name") or "").strip(),
        "current_level": "",
        "trend": "insufficient_data",
        "trend_evidence": stats.get("trend_evidence") or [],
        "weak_areas": [],
        "recommendations": [],
        "has_data": False,
        "total_submissions": stats.get("total_submissions", 0),
        "avg_score_rate": None,
    }


def _normalize_output(data: dict) -> dict:
    """Validate/coerce the model JSON into {current_level, recommendations}."""
    if not isinstance(data, dict):
        raise ValueError("model output is not a JSON object")
    current_level = str(data.get("current_level", "")).strip()[:LEVEL_MAX_CHARS]
    recommendations = [str(r).strip() for r in (data.get("recommendations") or [])
                       if str(r).strip()]
    if not current_level and not recommendations:
        raise ValueError("model output has neither current_level nor recommendations")
    return {"current_level": current_level,
            "recommendations": recommendations[:RECO_LIMIT]}


def analyze_student(student_id: int) -> dict:
    """Build one student's progress profile (see module docstring).

    All numbers come from compute_stats; the LLM only writes prose. Students
    with no usable records get a safe empty profile without any LLM call.

    Raises:
        ValueError:   student_id unknown.
        RuntimeError: LLM call failed or produced no usable JSON after retry.
    """
    student = db.get_student(student_id)
    if not student:
        raise ValueError(f"[tracker] unknown student_id: {student_id}")

    history = db.get_student_history(student_id)
    stats = compute_stats(history)
    stats["student_name"] = str(student.get("name") or "").strip()
    stats["year"] = student.get("year")
    stats["gender"] = student.get("gender")

    if stats["usable_count"] == 0:
        return _empty_profile(student, stats)

    system, user = build_tracker_prompt(stats)

    attempts = [
        (0.3, ""),
        (0.15, "\n\nIMPORTANT: your previous reply was not valid JSON or was "
               "missing the required fields. Reply with ONLY one complete JSON "
               "object, nothing else."),
    ]
    last_err = None
    for temp, extra in attempts:
        try:
            raw = complete(system, user + extra, temperature=float(temp))
            data = extract_json_block(raw)
            out = _normalize_output(data)
            break
        except Exception as exc:  # noqa: BLE001 - parse/validation blip -> one retry
            last_err = exc
    else:
        raise RuntimeError(
            f"[tracker.analyze_student] failed for student_id={student_id}: "
            f"{last_err}"
        )

    return {
        "student_id": student.get("id"),
        "student_name": stats["student_name"],
        "current_level": out["current_level"],
        "trend": stats["trend"],
        "trend_evidence": stats["trend_evidence"],
        "weak_areas": stats["weak_areas"],
        "recommendations": out["recommendations"],
        "has_data": True,
        "total_submissions": stats["total_submissions"],
        "avg_score_rate": stats["avg_score_rate"],
    }


if __name__ == "__main__":  # quick manual check (requires a real API key)
    import json as _json
    print(_json.dumps(analyze_student(1), ensure_ascii=False, indent=2))
