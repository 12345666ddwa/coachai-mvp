#!/usr/bin/env python3
"""
CoachAI — SQLite persistence layer (store.db)
=============================================

Phase 1 data layer for the three upcoming features:

    * report generation  (report_comments)
    * student tracking   (submissions / students summaries)
    * history lookup     (submissions queries)

Design rules
------------
    * Pure standard library (sqlite3) — zero third-party dependencies.
    * Thread-safe: Gradio serves requests from multiple threads, so every
      public function takes a module-level lock and opens a fresh short-
      lived connection per operation (no shared connection object).
    * Database path resolution order: explicit ``db_path`` argument > the
      ``COACH_AI_DB`` environment variable > ``<project>/data/coachai.db``.
      Parent directories are created automatically.
    * All timestamps are stored as UTC ISO-8601 strings, e.g.
      ``2026-09-25T08:15:42Z`` (lexicographically sortable).

Usage
-----
    from store import db
    db.init_db()
    sid = db.add_student("Alex Chen", year="Year 12", gender="M")
    db.record_submission("ec2025-q14", answer_text, result, student_id=sid)
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

# --------------------------------------------------------------------------
# Paths & global state
# --------------------------------------------------------------------------

# Project root = one level up from this file (store/db.py -> ai-coach/)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Default database location; override with the COACH_AI_DB env var.
DEFAULT_DB_PATH = os.path.join(_ROOT, "data", "coachai.db")

# One lock guards every DB operation. Standard-library sqlite3 handles are
# not safe to share across threads, so serialising access + one connection
# per operation is the simplest rock-solid scheme for this workload.
_LOCK = threading.RLock()

# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    year TEXT,                -- e.g. 'Year 11' / 'Year 12'
    gender TEXT,              -- 'M' / 'F' / NULL (used for pronouns in reports)
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,       -- nullable: anonymous grading is allowed
    question_id TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    marks_awarded REAL,
    max_marks INTEGER,
    confidence_pct INTEGER,
    confidence_level TEXT,    -- 'high' / 'medium' / 'low'
    status TEXT,              -- 'approved' / 'flagged' / 'error'
    feedback_json TEXT,       -- full marker/verifier result as JSON string
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    period TEXT,              -- e.g. 'Term 3 2026'
    comment_text TEXT,
    teacher_notes TEXT,       -- teacher's custom input that steered the AI comment
    generated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_submissions_student  ON submissions (student_id);
CREATE INDEX IF NOT EXISTS idx_submissions_question ON submissions (question_id);
CREATE INDEX IF NOT EXISTS idx_comments_student     ON report_comments (student_id);
CREATE INDEX IF NOT EXISTS idx_notes_student        ON custom_notes (student_id);
"""

# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------


def _resolve_db_path(db_path: Optional[str] = None) -> str:
    """Resolve which SQLite file to use.

    Priority: explicit ``db_path`` argument > ``COACH_AI_DB`` env var >
    :data:`DEFAULT_DB_PATH`. The result is always absolute.
    """
    if db_path:
        return os.path.abspath(db_path)
    env_path = os.environ.get("COACH_AI_DB")
    if env_path:
        return os.path.abspath(env_path)
    return DEFAULT_DB_PATH


@contextmanager
def _connect(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    """Open a fresh connection to the resolved database file.

    Creates the parent directory if missing, yields a connection with
    ``row_factory = sqlite3.Row``, and always closes it afterwards.
    """
    path = _resolve_db_path(db_path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _utc_now() -> str:
    """Current UTC time as an ISO-8601 string (e.g. '2026-09-25T08:15:42Z')."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_submission(row: sqlite3.Row) -> dict:
    """Convert a submissions row into a plain dict.

    The raw ``feedback_json`` column is kept as-is, and a decoded copy is
    exposed under the convenience key ``result`` (the full marker/verifier
    result dict; ``None`` if the JSON is absent or corrupt).
    """
    item = dict(row)
    raw = item.get("feedback_json")
    result: Optional[dict] = None
    if raw:
        try:
            result = json.loads(raw)
        except (ValueError, TypeError):
            result = None
    item["result"] = result
    return item


# --------------------------------------------------------------------------
# Initialisation
# --------------------------------------------------------------------------


def init_db(db_path: Optional[str] = None) -> None:
    """Create all tables (and indexes) if they do not exist yet.

    Idempotent — safe to call on every application start.

    Args:
        db_path: Optional explicit database file path. Falls back to the
            ``COACH_AI_DB`` environment variable, then to
            ``data/coachai.db`` in the project root.
    """
    with _LOCK, _connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


# --------------------------------------------------------------------------
# Students
# --------------------------------------------------------------------------


def add_student(name: str, year: Optional[str] = None,
                gender: Optional[str] = None) -> int:
    """Insert a new student and return the new row id.

    Duplicate names are allowed on purpose (create-new, never upsert);
    callers who need disambiguation should use :func:`find_student_by_name`.

    Args:
        name: Student display name (required, non-empty after stripping).
        year: Cohort label such as ``'Year 11'`` / ``'Year 12'`` (optional).
        gender: ``'M'`` / ``'F'`` or None — used for pronouns in reports.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("add_student: name must be a non-empty string")
    with _LOCK, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO students (name, year, gender, created_at) VALUES (?, ?, ?, ?)",
            (name, year, gender, _utc_now()),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_student(student_id: int) -> Optional[dict]:
    """Return one student as a dict, or None when the id does not exist."""
    with _LOCK, _connect() as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?", (student_id,)
        ).fetchone()
    return dict(row) if row else None


def find_student_by_name(name: str) -> list[dict]:
    """Fuzzy-match students by name (case-insensitive ``LIKE %name%``).

    Returns a list (possibly empty) ordered by id; multiple rows are
    expected for duplicated or partial names.
    """
    needle = f"%{(name or '').strip()}%"
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM students WHERE name LIKE ? ORDER BY id", (needle,)
        ).fetchall()
    return [dict(r) for r in rows]


def list_students() -> list[dict]:
    """Return every student, ordered by name (case-insensitive) then id."""
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM students ORDER BY name COLLATE NOCASE, id"
        ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# Submissions
# --------------------------------------------------------------------------


def record_submission(question_id: str, answer_text: str, result: dict,
                      student_id: Optional[int] = None) -> int:
    """Persist one grading result and return the new submission row id.

    Args:
        question_id: Question identifier, e.g. ``'ec2025-q14'``.
        answer_text: The student's raw answer text.
        result: The dict returned by the marking engine
            (``graphs.mark_graph.mark_answer``). All fields are read
            defensively via ``.get`` so partial/error results are fine;
            the whole dict is stored verbatim as ``feedback_json``.
        student_id: Optional student id; None means anonymous grading.

    Returns:
        The new submission's row id.
    """
    if not question_id or not str(question_id).strip():
        raise ValueError("record_submission: question_id must be non-empty")
    if not answer_text or not str(answer_text).strip():
        raise ValueError("record_submission: answer_text must be non-empty")
    result = result if isinstance(result, dict) else {}

    status = result.get("status")
    marks = result.get("marks")
    max_marks = result.get("max_marks")
    confidence_pct = result.get("confidence_pct")
    confidence_level = result.get("confidence_level")
    feedback_json = json.dumps(result, ensure_ascii=False)

    with _LOCK, _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO submissions
                (student_id, question_id, answer_text, marks_awarded, max_marks,
                 confidence_pct, confidence_level, status, feedback_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, str(question_id).strip(), answer_text,
             marks, max_marks, confidence_pct, confidence_level, status,
             feedback_json, _utc_now()),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_submissions(student_id: Optional[int] = None,
                    question_id: Optional[str] = None,
                    limit: int = 100) -> list[dict]:
    """Query submissions, newest first (``created_at DESC, id DESC``).

    Args:
        student_id: Optional filter by student.
        question_id: Optional filter by question.
        limit: Maximum number of rows to return (default 100).

    Returns:
        List of submission dicts (all columns, plus decoded ``result``).
    """
    where, params = [], []
    if student_id is not None:
        where.append("student_id = ?")
        params.append(student_id)
    if question_id is not None:
        where.append("question_id = ?")
        params.append(question_id)
    sql = "SELECT * FROM submissions"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
    params.append(int(limit))

    with _LOCK, _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_submission(r) for r in rows]


def get_student_history(student_id: int) -> list[dict]:
    """Return every submission of one student, oldest first.

    Ordered ``created_at ASC, id ASC`` so it can be plotted directly as a
    progress/trend line (issue: needs chronological order, unlike
    :func:`get_submissions` which is newest-first).
    """
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM submissions
            WHERE student_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (student_id,),
        ).fetchall()
    return [_row_to_submission(r) for r in rows]


def get_student_summary(student_id: int) -> dict:
    """Aggregate stats for the student-tracking feature.

    Returns a dict with:
        student:           the student row dict (or None if id unknown)
        student_id:        the queried id
        total_submissions: count of all rows recorded for this student
        avg_score_rate:    mean of ``marks_awarded / max_marks`` over rows
                           where both are usable (None if no usable rows)
        avg_marks:         mean of ``marks_awarded`` over usable rows
        recent_submissions: up to 5 latest submissions, newest first
        by_question:       list of per-question stats, ordered by question id:
                           {question_id, attempts, max_marks, marks (chronological
                            list of awarded marks), avg_marks, avg_score_rate}

    Never raises for an unknown or empty student — it returns a well-formed
    summary with zeros / Nones instead.
    """
    history = get_student_history(student_id)

    rates: list[float] = []
    marks_list: list[float] = []
    by_question: dict[str, dict[str, Any]] = {}
    for sub in history:
        marks = sub.get("marks_awarded")
        max_marks = sub.get("max_marks")
        qid = sub.get("question_id")
        bucket = by_question.setdefault(
            qid, {"question_id": qid, "attempts": 0, "max_marks": max_marks,
                  "marks": [], "_rates": []}
        )
        bucket["attempts"] += 1
        if max_marks:
            bucket["max_marks"] = max_marks
        if marks is not None:
            bucket["marks"].append(marks)
        if marks is not None and max_marks:  # usable score-rate row
            rate = float(marks) / float(max_marks)
            rates.append(rate)
            marks_list.append(float(marks))
            bucket["_rates"].append(rate)

    question_stats = []
    for qid in sorted(by_question):
        b = by_question[qid]
        stats = {
            "question_id": qid,
            "attempts": b["attempts"],
            "max_marks": b["max_marks"],
            "marks": b["marks"],
            "avg_marks": (round(sum(b["_rates"]) / len(b["_rates"]) * b["max_marks"], 4)
                          if b["_rates"] and b["max_marks"] else None),
            "avg_score_rate": (round(sum(b["_rates"]) / len(b["_rates"]), 4)
                               if b["_rates"] else None),
        }
        question_stats.append(stats)

    recent = list(reversed(history[-5:]))  # newest first

    return {
        "student": get_student(student_id),
        "student_id": student_id,
        "total_submissions": len(history),
        "avg_score_rate": round(sum(rates) / len(rates), 4) if rates else None,
        "avg_marks": round(sum(marks_list) / len(marks_list), 4) if marks_list else None,
        "recent_submissions": recent,
        "by_question": question_stats,
    }


# --------------------------------------------------------------------------
# Report comments (report-generation feature)
# --------------------------------------------------------------------------


def add_report_comment(student_id: int, period: Optional[str],
                       comment_text: Optional[str],
                       teacher_notes: Optional[str] = None) -> int:
    """Store one generated report comment and return its row id.

    Args:
        student_id: Target student id.
        period: Reporting period, e.g. ``'Term 3 2026'``.
        comment_text: The AI-generated (and possibly edited) comment text.
        teacher_notes: The teacher's own input that steered the generation.
    """
    with _LOCK, _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO report_comments
                (student_id, period, comment_text, teacher_notes, generated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, period, comment_text, teacher_notes, _utc_now()),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_report_comments(student_id: int,
                        period: Optional[str] = None) -> list[dict]:
    """Return report comments for a student, newest first.

    Args:
        student_id: Target student id.
        period: Optional exact-match filter, e.g. ``'Term 3 2026'``.
    """
    sql = "SELECT * FROM report_comments WHERE student_id = ?"
    params: list[Any] = [student_id]
    if period is not None:
        sql += " AND period = ?"
        params.append(period)
    sql += " ORDER BY generated_at DESC, id DESC"

    with _LOCK, _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# Custom notes (teacher free-form notes per student)
# --------------------------------------------------------------------------


def add_custom_note(student_id: int, note: Optional[str]) -> int:
    """Store one free-form teacher note for a student; returns its row id."""
    with _LOCK, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO custom_notes (student_id, note, created_at) VALUES (?, ?, ?)",
            (student_id, note, _utc_now()),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_custom_notes(student_id: int) -> list[dict]:
    """Return a student's custom notes, newest first."""
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM custom_notes
            WHERE student_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (student_id,),
        ).fetchall()
    return [dict(r) for r in rows]
