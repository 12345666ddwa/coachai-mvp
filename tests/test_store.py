#!/usr/bin/env python3
"""
CoachAI — store/db.py test suite (SQLite persistence layer).

Runs both ways:

    python3 tests/test_store.py     # plain asserts, prints PASS per test
    python3 -m pytest tests/test_store.py

Every test uses its own throwaway database via tempfile.TemporaryDirectory
(never the real data/coachai.db).
"""
import json
import os
import sqlite3
import sys
import tempfile
import threading
import traceback
from contextlib import contextmanager

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from store import db  # noqa: E402


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

@contextmanager
def fresh_db():
    """Create an empty temp database and point COACH_AI_DB at it.

    Yields the absolute db file path. The environment variable is restored
    afterwards so tests never leak state into each other or the real app.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test_coachai.db")
        old = os.environ.get("COACH_AI_DB")
        os.environ["COACH_AI_DB"] = path
        try:
            db.init_db()
            yield path
        finally:
            if old is None:
                os.environ.pop("COACH_AI_DB", None)
            else:
                os.environ["COACH_AI_DB"] = old


def sample_result(marks: int, max_marks: int, status: str = "approved",
                  conf: int = 85) -> dict:
    """A realistic marking-engine result dict (shape of mark_answer output)."""
    return {
        "question_id": "ec2025-q14",
        "status": status,
        "marks": marks,
        "max_marks": max_marks,
        "confidence_pct": conf,
        "confidence_level": "high" if conf >= 80 else ("medium" if conf >= 50 else "low"),
        "feedback": [
            {"type": "good", "text": "Quantified how memes spread."},
            {"type": "improve", "text": "Add the qualitative theme/tone analysis."},
        ],
        "flags": [],
        "attempts": 1,
        "justification": "band matched: describes two of three required strands.",
    }


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------

def test_init_db_idempotent():
    """init_db() must be safe to call repeatedly, and explicit paths work."""
    with fresh_db() as path:
        db.init_db()   # 2nd call
        db.init_db()   # 3rd call — must not raise
        assert os.path.exists(path)

        # explicit db_path wins over env; creates nested directories
        with tempfile.TemporaryDirectory() as tmp:
            explicit = os.path.join(tmp, "nested", "deep", "explicit.db")
            db.init_db(db_path=explicit)
            db.init_db(db_path=explicit)  # idempotent on explicit path too
            assert os.path.exists(explicit)

        # all four tables exist
        conn = sqlite3.connect(path)
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert {"students", "submissions", "report_comments", "custom_notes"} <= names


def test_add_and_get_student():
    """add_student → get_student roundtrip; duplicates allowed; None on miss."""
    with fresh_db():
        sid = db.add_student("Alex Chen", year="Year 12", gender="M")
        assert isinstance(sid, int) and sid > 0

        s = db.get_student(sid)
        assert s is not None
        assert s["name"] == "Alex Chen"
        assert s["year"] == "Year 12"
        assert s["gender"] == "M"
        assert s["created_at"].endswith("Z")          # UTC ISO timestamp

        # same name twice → two rows (no uniqueness constraint)
        sid2 = db.add_student("Alex Chen")
        assert sid2 != sid
        assert db.get_student(student_id=999999) is None

        # find (fuzzy) + list
        hits = db.find_student_by_name("chen")        # case-insensitive substring
        assert len(hits) == 2 and all(h["name"] == "Alex Chen" for h in hits)
        assert db.find_student_by_name("Nobody") == []
        all_students = db.list_students()
        assert len(all_students) == 2


def test_record_and_filter_submissions():
    """record_submission persists; get_submissions filters by student/question."""
    with fresh_db():
        alex = db.add_student("Alex Chen")
        priya = db.add_student("Priya Sharma")

        db.record_submission("ec2025-q14", "alex answer 1",
                             sample_result(3, 3), student_id=alex)
        db.record_submission("ec2025-q16a", "alex answer 2",
                             sample_result(3, 4), student_id=alex)
        db.record_submission("ec2025-q14", "priya answer",
                             sample_result(2, 3), student_id=priya)
        db.record_submission("ec2025-q14", "anonymous answer",
                             sample_result(1, 3, status="flagged", conf=45))

        assert len(db.get_submissions()) == 4
        assert len(db.get_submissions(student_id=alex)) == 2
        assert len(db.get_submissions(student_id=priya)) == 1
        assert len(db.get_submissions(question_id="ec2025-q14")) == 3
        assert len(db.get_submissions(student_id=alex, question_id="ec2025-q14")) == 1
        assert len(db.get_submissions(question_id="ec2025-q99")) == 0

        # newest first
        ids = [s["id"] for s in db.get_submissions()]
        assert ids == sorted(ids, reverse=True), ids

        # limit is honoured
        assert len(db.get_submissions(limit=2)) == 2

        # column roundtrip + decoded result JSON (ensure_ascii=False path)
        s = db.get_submissions(student_id=alex, question_id="ec2025-q16a")[0]
        assert s["student_id"] == alex
        assert s["question_id"] == "ec2025-q16a"
        assert s["answer_text"] == "alex answer 2"
        assert s["marks_awarded"] == 3 and s["max_marks"] == 4
        assert s["confidence_pct"] == 85 and s["confidence_level"] == "high"
        assert s["status"] == "approved"
        assert isinstance(s["feedback_json"], str)
        assert s["result"]["feedback"][0]["type"] == "good"

        # anonymous submission has student_id NULL
        anon = db.get_submissions(question_id="ec2025-q14")
        assert any(x["student_id"] is None for x in anon)

        # error results (missing marks/max_marks) must still store cleanly
        db.record_submission("ec2025-q14", "engine blew up",
                             {"status": "error", "error": "timeout"},
                             student_id=alex)
        err = db.get_submissions(student_id=alex)[0]
        assert err["status"] == "error" and err["marks_awarded"] is None


def test_student_history_order():
    """get_student_history returns that student's rows in chronological order."""
    with fresh_db():
        sam = db.add_student("Sam Taylor")
        other = db.add_student("Other Student")
        for i in range(3):
            db.record_submission("ec2025-q14", f"sam answer {i}",
                                 sample_result(i + 1, 3), student_id=sam)
        db.record_submission("ec2025-q14", "interloper", sample_result(3, 3),
                             student_id=other)

        hist = db.get_student_history(sam)
        assert [h["answer_text"] for h in hist] == [
            "sam answer 0", "sam answer 1", "sam answer 2"]      # oldest → newest
        assert [h["marks_awarded"] for h in hist] == [1, 2, 3]
        assert all(h["student_id"] == sam for h in hist)
        assert db.get_student_history(other)[0]["answer_text"] == "interloper"
        assert db.get_student_history(12345) == []


def test_student_summary_aggregation():
    """get_student_summary averages score rates over known records."""
    with fresh_db():
        alex = db.add_student("Alex Chen", year="Year 12", gender="M")
        # 3 known records on a 4-mark question: 1/4, 2/4, 3/4
        for marks in (1, 2, 3):
            db.record_submission("ec2025-q16a", f"answer {marks}",
                                 sample_result(marks, 4), student_id=alex)

        summary = db.get_student_summary(alex)
        assert summary["student"]["name"] == "Alex Chen"
        assert summary["student_id"] == alex
        assert summary["total_submissions"] == 3
        # mean of (0.25, 0.5, 0.75) = 0.5
        assert abs(summary["avg_score_rate"] - 0.5) < 1e-9, summary["avg_score_rate"]
        assert abs(summary["avg_marks"] - 2.0) < 1e-9, summary["avg_marks"]

        # recent_submissions: newest first, at most 5
        recent = summary["recent_submissions"]
        assert [r["marks_awarded"] for r in recent] == [3, 2, 1]

        # by_question: chronological marks list + per-question average
        assert len(summary["by_question"]) == 1
        q = summary["by_question"][0]
        assert q["question_id"] == "ec2025-q16a"
        assert q["attempts"] == 3 and q["max_marks"] == 4
        assert q["marks"] == [1, 2, 3]
        assert abs(q["avg_score_rate"] - 0.5) < 1e-9
        assert abs(q["avg_marks"] - 2.0) < 1e-9

        # a record with no usable marks counts in total but not in the average
        db.record_submission("ec2025-q14", "errored run",
                             {"status": "error", "error": "x"}, student_id=alex)
        summary = db.get_student_summary(alex)
        assert summary["total_submissions"] == 4
        assert abs(summary["avg_score_rate"] - 0.5) < 1e-9

        # multiple questions → stats grouped per question
        db.record_submission("ec2025-q14", "new q", sample_result(2, 3),
                             student_id=alex)
        summary = db.get_student_summary(alex)
        assert [q["question_id"] for q in summary["by_question"]] == [
            "ec2025-q14", "ec2025-q16a"]

        # unknown / empty student → well-formed zeros, no crash
        empty = db.get_student_summary(999999)
        assert empty["total_submissions"] == 0
        assert empty["avg_score_rate"] is None
        assert empty["student"] is None
        assert empty["recent_submissions"] == [] and empty["by_question"] == []


def test_report_comments_roundtrip():
    """add_report_comment / get_report_comments with and without period filter."""
    with fresh_db():
        priya = db.add_student("Priya Sharma", year="Year 12", gender="F")
        cid1 = db.add_report_comment(
            priya, "Term 3 2026", "Priya consistently demonstrates strong analysis.",
            teacher_notes="Mention her improvement in security questions.")
        cid2 = db.add_report_comment(priya, "Term 4 2026", "Continued growth.")
        assert cid1 and cid2 and cid1 != cid2

        comments = db.get_report_comments(priya)
        assert len(comments) == 2
        assert comments[0]["period"] == "Term 4 2026"       # newest first
        assert comments[1]["teacher_notes"] == ("Mention her improvement "
                                                "in security questions.")
        assert comments[0]["generated_at"].endswith("Z")

        t3 = db.get_report_comments(priya, period="Term 3 2026")
        assert len(t3) == 1
        assert t3[0]["comment_text"].startswith("Priya consistently")
        assert db.get_report_comments(priya, period="Term 1 2026") == []
        assert db.get_report_comments(999999) == []


def test_custom_notes_roundtrip():
    """add_custom_note / get_custom_notes basic roundtrip."""
    with fresh_db():
        sam = db.add_student("Sam Taylor")
        nid = db.add_custom_note(sam, "Needs revision of data mining concepts.")
        assert nid > 0

        notes = db.get_custom_notes(sam)
        assert len(notes) == 1
        assert notes[0]["note"] == "Needs revision of data mining concepts."
        assert notes[0]["created_at"].endswith("Z")

        db.add_custom_note(sam, "Second note about report preparation.")
        notes = db.get_custom_notes(sam)
        assert len(notes) == 2
        assert notes[0]["note"].startswith("Second")        # newest first
        assert db.get_custom_notes(999999) == []


def test_thread_safety_concurrent_writes():
    """Gradio is multi-threaded: concurrent writers must not corrupt/crash."""
    with fresh_db():
        sid = db.add_student("Threads McGee")
        errors = []

        def worker(k: int) -> None:
            try:
                for i in range(8):
                    db.record_submission(
                        "ec2025-q14", f"thread {k} answer {i}",
                        sample_result(1, 3), student_id=sid)
            except Exception as exc:  # pragma: no cover - only on failure
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(k,)) for k in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, errors
        assert len(db.get_submissions(student_id=sid, limit=100)) == 40


def test_json_feedback_preserves_unicode():
    """feedback_json is written with ensure_ascii=False (readable UTF-8)."""
    with fresh_db():
        sid = db.add_student("Chen 陈")
        db.record_submission("ec2025-q14", "答案",
                             {"status": "approved", "marks": 1, "max_marks": 3,
                              "note": "学生进步明显"}, student_id=sid)
        row = db.get_submissions(student_id=sid)[0]
        assert "学生进步明显" in row["feedback_json"]        # not \uXXXX escaped
        assert row["result"]["note"] == "学生进步明显"


# --------------------------------------------------------------------------
# runner (python3 tests/test_store.py)
# --------------------------------------------------------------------------

def _run_all() -> int:
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failed = []
    for name, fn in tests:
        try:
            fn()
        except Exception:  # noqa: BLE001
            failed.append(name)
            print(f"FAIL: {name}")
            traceback.print_exc()
        else:
            print(f"PASS: {name}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} tests passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_run_all())
