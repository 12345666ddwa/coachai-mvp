#!/usr/bin/env python3
"""
CoachAI — demo data seeder for the SQLite store layer (tests/seed_golden.py)
============================================================================

Seeds the CoachAI database (default ``data/coachai.db``; override with the
``COACH_AI_DB`` env var) with three DEMO students and realistic grading
histories, so the upcoming report-generation / student-tracking / history
features have something believable to display.

    ** DEMO DATA ONLY ** — 'Alex Chen', 'Priya Sharma' and 'Sam Taylor' are
    invented students, not real people. Never ship this database as-is.

Data source: ``tests/golden_set.json`` — 8 real 2025 HSC Enterprise
Computing questions, each with 4 band-graded sample answers
(excellent / good / weak / borderline). Mark mapping: every answer in the
golden set already carries ``expected_marks`` (the CoachAI team's
band-derived score, checked against the official NESA marking guidelines),
so we use it directly:  marks = answer.expected_marks,
max_marks = question item's ``marks``.

Demo stories (deliberately different shapes for trend charts):
    * Alex Chen  — improving: the same question revisited, 1 → 2 → 3 / 3.
    * Priya Sharma — stable strong performer across several topics (~75-100%).
    * Sam Taylor — fluctuating: a dip in the middle, then recovery.

Idempotent-ish: re-running reuses existing demo students by exact name and
skips any student who already has submissions, so it is safe to run twice.

Run:  python3 tests/seed_golden.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from store import db as store_db  # noqa: E402

GOLDEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "golden_set.json")

# --------------------------------------------------------------------------
# Demo plan: which golden answers each demo student "submitted", which day,
# and how confident the engine was. Status mirrors the real pipeline
# (flagged = low-agreement / low-confidence runs needing human review).
# --------------------------------------------------------------------------

FEEDBACK_TEMPLATES = {
    # quality -> (positive note, improvement note)
    "excellent": (
        "Addresses every required strand of the question with specific, "
        "relevant detail.",
        "Keep applying this depth consistently under exam time pressure.",
    ),
    "good": (
        "Covers the main ideas needed for the middle band, with mostly "
        "accurate terminology.",
        "Add concrete detail or examples to lift this into the top band.",
    ),
    "weak": (
        "Makes at least one relevant point relating to the question.",
        "Re-read the question's action verb and build the answer around "
        "specific examples rather than general statements.",
    ),
    "borderline": (
        "Meets most requirements of the middle band but one strand is "
        "thinly developed.",
        "Tighten the weaker strand with rubric wording so the answer "
        "clearly reaches the higher band.",
    ),
}

DEMO_PLAN = [
    {
        "name": "Alex Chen",
        "year": "Year 12",
        "gender": "M",
        "story": "improving — revisited the same question three times, 1 → 3 / 3",
        "records": [
            # (question_id, quality, days_ago, status, confidence_pct)
            ("ec2025-q14", "weak", 28, "flagged", 48),
            ("ec2025-q14", "good", 21, "approved", 82),
            ("ec2025-q14", "excellent", 14, "approved", 91),
        ],
        "note": ("First attempts missed the data-analysis strand; by late Term 3 "
                 "communicates the full method cleanly. Encouraged by practice "
                 "questions."),
        "comment": (
            "Alex has made encouraging progress this term. Early responses "
            "focused on surface features of the question, but recent work shows "
            "a stronger grasp of how data analysis supports business decisions, "
            "with clearer use of specific examples. Continued practice with "
            "higher-mark questions will consolidate this improvement."
        ),
        "teacher_notes": "Emphasise the improvement trend and encourage him.",
    },
    {
        "name": "Priya Sharma",
        "year": "Year 12",
        "gender": "F",
        "story": "stable — consistent mid-to-high marks across topics (~75-100%)",
        "records": [
            ("ec2025-q16a", "good", 30, "approved", 84),
            ("ec2025-q16b", "good", 23, "approved", 81),
            ("ec2025-q20", "excellent", 16, "approved", 90),
            ("ec2025-q24", "good", 9, "approved", 83),
        ],
        "note": ("Reliable across every topic assessed this term; depth in "
                 "extended-response questions is the next focus."),
        "comment": (
            "Priya performs consistently at a strong level across the Enterprise "
            "Computing topics assessed this term. Her answers are well "
            "structured and use appropriate terminology; the next step is to add "
            "greater depth in extended-response questions to consistently reach "
            "the top band."
        ),
        "teacher_notes": "Keep tone encouraging but push for the top band.",
    },
    {
        "name": "Sam Taylor",
        "year": "Year 11",
        "gender": "M",
        "story": "fluctuating — good start, mid-term dip, then recovery",
        "records": [
            ("ec2025-q14", "good", 25, "approved", 79),
            ("ec2025-q20", "weak", 18, "flagged", 47),
            ("ec2025-q22b", "borderline", 11, "flagged", 68),
            ("ec2025-q17a", "excellent", 4, "approved", 88),
        ],
        "note": ("Careless omissions cost marks in weeks 2-3; recovered well on "
                 "the data-warehousing question once he revised the definitions."),
        "comment": (
            "Sam's results this term have fluctuated with the difficulty of the "
            "topic. When questions connect to familiar contexts he performs "
            "well, but careless omissions cost marks in others. Regular revision "
            "of key definitions and careful attention to the question's action "
            "verb are recommended."
        ),
        "teacher_notes": "Mention the dip in the spreadsheet-visualisation topic.",
    },
]

# How long ago the demo students were "created" (before their first records).
STUDENT_AGE_DAYS = 36


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def load_golden() -> dict[str, dict]:
    """Load golden_set.json into {question_id: item} for easy lookup."""
    with open(GOLDEN_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return {item["question_id"]: item for item in data["items"]}


def confidence_level(pct: int) -> str:
    """Same thresholds as graphs/mark_graph._confidence_level."""
    if pct >= 80:
        return "high"
    if pct >= 50:
        return "medium"
    return "low"


def build_result(question_id: str, marks: int, max_marks: int, status: str,
                 conf_pct: int, quality: str) -> dict:
    """Fabricate a realistic marking-engine result dict for a demo record.

    Shape matches graphs/mark_graph.mark_answer() output so downstream code
    (history views, trend charts, reports) parses demo rows exactly like
    real ones.
    """
    good_text, improve_text = FEEDBACK_TEMPLATES[quality]
    flags = []
    if status == "flagged":
        flags = ["Marker/verifier band disagreement — human review suggested."]
    return {
        "question_id": question_id,
        "status": status,
        "marks": marks,
        "max_marks": max_marks,
        "confidence_pct": conf_pct,
        "confidence_level": confidence_level(conf_pct),
        "feedback": [
            {"type": "good", "text": good_text},
            {"type": "improve", "text": improve_text},
        ],
        "flags": flags,
        "attempts": 2 if status == "flagged" else 1,
        "justification": (
            f"Demo record — derived from golden_set '{quality}' sample answer "
            f"(band-derived mark {marks}/{max_marks})."
        ),
    }


def utc_days_ago(days: float) -> str:
    """UTC ISO timestamp string for 'now minus N days'."""
    ts = datetime.now(timezone.utc) - timedelta(days=days)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def backdate(db_path: str, table: str, column: str, row_id: int,
             days_ago: float) -> None:
    """Rewrite one row's timestamp so the demo history spreads over weeks.

    ``record_submission``/``add_student`` always stamp "now"; for believable
    trend charts we post-adjust the timestamps of just-inserted demo rows
    (direct UPDATE on the same DB file — demo script only, not app code).
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            f"UPDATE {table} SET {column} = ? WHERE id = ?",  # noqa: S608 (fixed names)
            (utc_days_ago(days_ago), row_id),
        )
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    golden = load_golden()
    db_path = store_db._resolve_db_path()  # private helper = single source of truth
    store_db.init_db()

    print("=" * 78)
    print("CoachAI demo seed — tests/golden_set.json  →  SQLite")
    print("DEMO DATA ONLY — these students are fake, do not ship the DB as-is")
    print("=" * 78)

    demo_sids: list[int] = []
    inserted = {"records": 0, "notes": 0, "comments": 0}

    for i, plan in enumerate(DEMO_PLAN, start=1):
        name = plan["name"]

        # --- reuse an exact-name demo student if this script ran before ----
        existing = [s for s in store_db.find_student_by_name(name)
                    if s["name"] == name]
        if existing:
            sid = existing[0]["id"]
            created = False
        else:
            sid = store_db.add_student(name, year=plan["year"],
                                       gender=plan["gender"])
            backdate(db_path, "students", "created_at", sid, STUDENT_AGE_DAYS)
            created = True
        demo_sids.append(sid)

        print(f"\n[{i}/{len(DEMO_PLAN)}] {name} ({plan['year']}, "
              f"{plan['gender']})  → student id={sid}")
        print(f"      story: {plan['story']}")

        already = store_db.get_submissions(student_id=sid, limit=1)
        if already or (not created and store_db.get_custom_notes(sid)):
            print("      (already seeded — skipping records/comments)")
            continue

        # --- submissions: real golden-set questions + answers --------------
        for qid, quality, days_ago, status, conf in plan["records"]:
            item = golden[qid]
            answer = next(a for a in item["answers"] if a["quality"] == quality)
            marks = int(answer["expected_marks"])
            max_marks = int(item["marks"])
            result = build_result(qid, marks, max_marks, status, conf, quality)

            sub_id = store_db.record_submission(
                qid, answer["text"], result, student_id=sid)
            backdate(db_path, "submissions", "created_at", sub_id, days_ago)

            rate = marks / max_marks if max_marks else 0
            print(f"      sub #{sub_id:<3} {utc_days_ago(days_ago)[:10]}  "
                  f"{qid:<12} {quality:<10} {marks}/{max_marks} "
                  f"({rate:>4.0%})  {status:<8} conf {conf}%")
            inserted["records"] += 1

        # --- one teacher note + one draft report comment per demo student --
        store_db.add_custom_note(sid, plan["note"])
        backdate(db_path, "custom_notes", "created_at",
                 store_db.get_custom_notes(sid)[0]["id"], 6)
        inserted["notes"] += 1

        if not store_db.get_report_comments(sid, period="Term 3 2026"):
            cid = store_db.add_report_comment(
                sid, "Term 3 2026", plan["comment"],
                teacher_notes=plan["teacher_notes"])
            backdate(db_path, "report_comments", "generated_at", cid, 3)
            inserted["comments"] += 1
            print(f"      report comment #{cid} (Term 3 2026, draft)")

    # -------- summary -------------------------------------------------------
    n_students = len(demo_sids)
    n_records = sum(len(store_db.get_student_history(sid)) for sid in demo_sids)
    n_notes = sum(len(store_db.get_custom_notes(sid)) for sid in demo_sids)
    n_comments = sum(len(store_db.get_report_comments(sid)) for sid in demo_sids)
    print("\n" + "=" * 78)
    print("Demo summary")
    print(f"  students      : {n_students}  "
          f"({', '.join(p['name'] for p in DEMO_PLAN)})")
    print(f"  submissions   : {n_records}")
    print(f"  custom notes  : {n_notes}")
    print(f"  report cmts   : {n_comments} (Term 3 2026 drafts)")
    if any(inserted.values()):
        print(f"  inserted this run : {inserted['records']} submissions, "
              f"{inserted['notes']} notes, {inserted['comments']} comments")
    print(f"  database file : {db_path}")
    print("=" * 78)
    if not any(inserted.values()):
        print("Nothing new was inserted (database already seeded).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
