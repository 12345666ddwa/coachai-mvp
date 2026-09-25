#!/usr/bin/env python3
"""
CoachAI Phase 5 test suite: agents/tracker.py + agents/report_writer.py.

Runs both ways:

    python3 tests/test_students.py
    python3 -m pytest tests/test_students.py

NO real LLM calls and NO real database writes: every test builds its own
throwaway SQLite file via tempfile + COACH_AI_DB (data/coachai.db is never
touched), and complete() is monkeypatched per test (plain setattr, so the
file also runs without pytest). Covers: deterministic trend detection
(improving / declining / volatile / stable), deterministic weak areas and
evidence, prompt assembly (student name, teacher notes, pronouns), the
report-writer and tracker contracts with a mocked LLM, the one-retry-on-
invalid-JSON behaviour, and the safe no-records paths.
"""
import json
import os
import sys
import tempfile
import traceback
from contextlib import contextmanager

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents import report_writer as rw  # noqa: E402
from agents import tracker as tr  # noqa: E402
from store import db  # noqa: E402


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

@contextmanager
def fresh_db():
    """Create an empty temp database and point COACH_AI_DB at it."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test_students.db")
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


@contextmanager
def patched(module, **attrs):
    """Temporarily replace module attributes (save + restore)."""
    saved = {k: getattr(module, k) for k in attrs}
    for k, v in attrs.items():
        setattr(module, k, v)
    try:
        yield module
    finally:
        for k, v in saved.items():
            setattr(module, k, v)


def fake_complete_factory(replies, calls):
    """Build a complete() stand-in. `replies` items are str or Exception."""
    def _fake(system_prompt, user_prompt, temperature=0.3, model=None,
              provider="deepseek", max_tokens=4096):
        calls.append({"system": system_prompt, "user": user_prompt,
                      "temperature": temperature})
        reply = replies.pop(0) if len(replies) > 1 else replies[0]
        if isinstance(reply, Exception):
            raise reply
        return reply
    return _fake


def add_record(student_id, qid, marks, max_marks, status="approved"):
    """Record one submission quickly (feedback_json shape kept realistic)."""
    db.record_submission(qid, f"answer {qid} {marks}", {
        "question_id": qid, "status": status, "marks": marks, "max_marks": max_marks,
        "confidence_pct": 85, "confidence_level": "high",
        "feedback": [], "flags": [], "attempts": 1, "justification": "test",
    }, student_id=student_id)


def make_student_with_rates(name, rates, qid="ec2025-q14", max_marks=10,
                            year="Year 12", gender: str | None = "M"):
    """Insert a student whose chronological score rates equal `rates`."""
    sid = db.add_student(name, year=year, gender=gender)
    for rate in rates:
        add_record(sid, qid, round(rate * max_marks), max_marks)
    return sid


FAKE_REPORT = {
    "comment": ("Alex has made steady progress in Enterprise Computing this term. "
                "His analysis tasks now show accurate use of syllabus terminology. "
                "Next term he should focus on extending his responses with evidence."),
    "evidence": ["q14: 3/3 on the most recent attempt", "Improving trend across four attempts"],
    "self_eval_note": "Which topic do I want to feel more confident about next term?",
}
FAKE_PROFILE = {
    "current_level": "Alex is performing at a sound level and improving.",
    "recommendations": ["Revise q14 data-handling terminology with practice tasks.",
                        "Extend answer length with evidence-based examples."],
}


# --------------------------------------------------------------------------
# deterministic trend detection (compute_stats)
# --------------------------------------------------------------------------

def test_trend_improving():
    with fresh_db():
        sid = make_student_with_rates("Imp", [0.2, 0.4, 0.6, 0.8])
        stats = tr.compute_stats(db.get_student_history(sid))
    assert stats["trend"] == "improving", stats["trend"]
    assert abs(stats["avg_score_rate"] - 0.5) < 1e-9
    assert stats["usable_count"] == 4
    assert stats["trend_evidence"], "evidence bullets must be produced"
    assert any("improving" in e for e in stats["trend_evidence"])


def test_trend_declining():
    with fresh_db():
        sid = make_student_with_rates("Dec", [0.9, 0.7, 0.5, 0.3])
        stats = tr.compute_stats(db.get_student_history(sid))
    assert stats["trend"] == "declining", stats["trend"]


def test_trend_volatile():
    with fresh_db():
        sid = make_student_with_rates("Vol", [0.4, 0.9, 0.4, 0.9])
        stats = tr.compute_stats(db.get_student_history(sid))
    assert stats["trend"] == "volatile", stats["trend"]


def test_trend_stable():
    with fresh_db():
        sid = make_student_with_rates("Sta", [0.6, 0.6, 0.6, 0.6])
        stats = tr.compute_stats(db.get_student_history(sid))
        assert stats["trend"] == "stable", stats["trend"]
        # a single attempt cannot carry a direction (same temp db, never the real one)
        sid2 = make_student_with_rates("One", [0.8])
        stats2 = tr.compute_stats(db.get_student_history(sid2))
    assert stats2["trend"] == "insufficient_data"


def test_weak_areas_and_stats_are_deterministic():
    with fresh_db():
        sid = db.add_student("Weak Areas", year="Year 12", gender="F")
        # q14 averages 0.2 (weak), q16 averages 0.8 (not weak), one errored row
        for m in (1, 1, 2):
            add_record(sid, "ec2025-q14", m, 5)
        add_record(sid, "ec2025-q16a", 8, 10)
        db.record_submission("ec2025-q20", "engine blew up",
                             {"status": "error", "error": "x"}, student_id=sid)
        stats = tr.compute_stats(db.get_student_history(sid))

    assert stats["total_submissions"] == 5          # errors still counted
    assert stats["usable_count"] == 4               # but excluded from rates
    weak = stats["weak_areas"]
    assert len(weak) == 1 and "ec2025-q14" in weak[0]
    assert "27%" in weak[0]                      # mean of 0.20, 0.20, 0.40
    by_q = {q["question_id"]: q for q in stats["by_question"]}
    assert by_q["ec2025-q14"]["attempts"] == 3
    assert abs(by_q["ec2025-q14"]["avg_score_rate"] - round(4 / 15, 4)) < 1e-9
    assert by_q["ec2025-q16a"]["avg_score_rate"] == 0.8


def test_compute_stats_empty_and_single():
    stats = tr.compute_stats([])
    assert stats["total_submissions"] == 0
    assert stats["avg_score_rate"] is None
    assert stats["trend"] == "insufficient_data"
    assert stats["weak_areas"] == [] and stats["by_question"] == []


# --------------------------------------------------------------------------
# report writer: prompt assembly
# --------------------------------------------------------------------------

def _student_and_context(gender):
    sid = make_student_with_rates(f"Prompt {gender}", [0.5, 0.7], gender=gender)
    student = db.get_student(sid)
    return student, db.get_student_summary(sid), db.get_student_history(sid)


def test_report_prompt_contains_name_notes_and_pronouns():
    with fresh_db():
        stu_m, summary_m, hist_m = _student_and_context("M")
        student_f = db.get_student(make_student_with_rates("Prompt F", [0.5], gender="F"))
        student_x = db.get_student(make_student_with_rates("Prompt X", [0.5], gender=None))
    assert stu_m is not None and student_f is not None and student_x is not None

    notes = "Mention his improved cybersecurity quiz result."
    _, user = rw.build_report_prompt(stu_m, summary_m, hist_m, "Term 3 2026",
                                     teacher_notes=notes, extra_notes="Debating captain.")
    assert stu_m["name"] in user
    assert "Term 3 2026" in user
    assert notes in user                       # teacher notes reach the prompt
    assert "Debating captain." in user         # extra context too
    assert "he / him / his" in user            # male pronouns
    assert "ec2025-q14" in user                # per-question evidence
    assert "total_submissions" not in user.lower() or "Submissions recorded" in user

    _, user_f = rw.build_report_prompt(student_f, {"by_question": []}, [], "T1")
    assert "she / her / her" in user_f
    _, user_x = rw.build_report_prompt(student_x, {"by_question": []}, [], "T1")
    assert "they / them / their" in user_x     # unknown gender -> neutral pronouns


def test_report_prompt_no_records_note():
    with fresh_db():
        sid = db.add_student("No Records", year="Year 11", gender="M")
        student = db.get_student(sid)
    _, user = rw.build_report_prompt(student, {"by_question": []}, [], "Term 3 2026")
    assert "no marking records yet" in user
    assert "(No teacher notes provided" in user


# --------------------------------------------------------------------------
# report writer: generation with a mocked LLM
# --------------------------------------------------------------------------

def test_generate_report_comment_success():
    with fresh_db():
        sid = make_student_with_rates("Alex Chen", [0.33, 0.67, 1.0])
        calls = []
        with patched(rw, complete=fake_complete_factory([json.dumps(FAKE_REPORT)], calls)):
            out = rw.generate_report_comment(
                sid, "Term 3 2026", teacher_notes="Improved confidence in class discussion.")
    assert len(calls) == 1 and calls[0]["temperature"] == 0.4
    assert "Alex Chen" in calls[0]["user"]
    assert "Improved confidence in class discussion." in calls[0]["user"]
    # contract keys, with identity fields trusted from the db, not the model
    for key in ("student_id", "student_name", "period", "comment", "evidence",
                "self_eval_note"):
        assert key in out, f"missing key: {key}"
    assert out["student_id"] == sid and out["student_name"] == "Alex Chen"
    assert out["period"] == "Term 3 2026"
    assert out["comment"] == FAKE_REPORT["comment"]
    assert out["evidence"] == FAKE_REPORT["evidence"]
    assert out["self_eval_note"] == FAKE_REPORT["self_eval_note"]
    assert out["teacher_notes"] == "Improved confidence in class discussion."
    # model-provided fake identity must be ignored
    assert out["student_name"] != "Somebody Else"


def test_generate_report_comment_ignores_model_identity_fields():
    with fresh_db():
        sid = make_student_with_rates("Real Name", [0.5])
        fake = dict(FAKE_REPORT, student_id=999, student_name="Impostor", period="T0")
        calls = []
        with patched(rw, complete=fake_complete_factory([json.dumps(fake)], calls)):
            out = rw.generate_report_comment(sid, "Term 3 2026")
    assert out["student_id"] == sid and out["student_name"] == "Real Name"
    assert out["period"] == "Term 3 2026"


def test_generate_report_comment_retry_on_invalid_json():
    with fresh_db():
        sid = make_student_with_rates("Retry R", [0.5])
        calls = []
        replies = ["I cannot write that.", json.dumps(FAKE_REPORT)]
        with patched(rw, complete=fake_complete_factory(replies, calls)):
            out = rw.generate_report_comment(sid, "Term 3 2026")
    assert len(calls) == 2                       # first parse failed, retried once
    assert calls[0]["temperature"] == 0.4 and calls[1]["temperature"] == 0.2
    assert "not valid JSON" in calls[1]["user"]  # retry prompt is stricter
    assert out["comment"] == FAKE_REPORT["comment"]


def test_generate_report_comment_thin_json_retries_and_raises():
    with fresh_db():
        sid = make_student_with_rates("Thin T", [0.5])
        calls = []
        replies = [json.dumps({"evidence": ["x"]}), json.dumps({"comment": ""})]
        with patched(rw, complete=fake_complete_factory(replies, calls)):
            try:
                rw.generate_report_comment(sid, "Term 3 2026")
            except RuntimeError as exc:
                assert "failed" in str(exc)
            else:
                raise AssertionError("expected RuntimeError when both replies are unusable")
    assert len(calls) == 2


def test_generate_report_comment_no_records_is_safe():
    with fresh_db():
        sid = db.add_student("Fresh Student", year="Year 11", gender="F")
        calls = []
        with patched(rw, complete=fake_complete_factory([json.dumps(FAKE_REPORT)], calls)):
            out = rw.generate_report_comment(sid, "Term 3 2026",
                                             teacher_notes="Settled in well this term.")
    assert "no marking records yet" in calls[0]["user"]
    assert "Settled in well this term." in calls[0]["user"]
    assert out["student_id"] == sid and out["comment"]


def test_generate_report_comment_unknown_student_raises():
    with fresh_db():
        try:
            rw.generate_report_comment(999999, "Term 3 2026")
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for an unknown student id")


# --------------------------------------------------------------------------
# tracker: analyze_student with a mocked LLM
# --------------------------------------------------------------------------

def test_analyze_student_no_records_skips_llm():
    with fresh_db():
        sid = db.add_student("Empty Profile", year="Year 11", gender="M")
        calls = []
        with patched(tr, complete=fake_complete_factory(["SHOULD NOT BE CALLED"], calls)):
            profile = tr.analyze_student(sid)
    assert calls == []                            # no LLM call without data
    assert profile["student_id"] == sid
    assert profile["student_name"] == "Empty Profile"
    assert profile["has_data"] is False
    assert profile["trend"] == "insufficient_data"
    assert profile["current_level"] == ""
    assert profile["weak_areas"] == [] and profile["recommendations"] == []


def test_analyze_student_with_mocked_llm():
    with fresh_db():
        sid = make_student_with_rates("Alex Chen", [0.2, 0.4, 0.6, 0.8])
        calls = []
        with patched(tr, complete=fake_complete_factory([json.dumps(FAKE_PROFILE)], calls)):
            profile = tr.analyze_student(sid)
    assert len(calls) == 1
    sent = calls[0]["user"]
    # the aggregate numbers are handed to the model ready-made
    assert "Trend (deterministic): improving" in sent
    assert "Average score rate: 50%" in sent
    assert "EC2025" not in sent.upper() or "ec2025" in sent
    # deterministic fields survive whichever prose the model writes
    assert profile["trend"] == "improving"
    assert profile["trend_evidence"] and profile["has_data"] is True
    assert abs(profile["avg_score_rate"] - 0.5) < 1e-9
    assert profile["total_submissions"] == 4
    # LLM-written fields come through
    assert profile["current_level"] == FAKE_PROFILE["current_level"]
    assert profile["recommendations"] == FAKE_PROFILE["recommendations"]


def test_analyze_student_weak_areas_deterministic():
    with fresh_db():
        sid = db.add_student("Mixed", year="Year 12", gender="F")
        for m in (1, 1, 1):
            add_record(sid, "ec2025-q14", m, 5)     # 20% average -> weak
        add_record(sid, "ec2025-q16a", 9, 10)       # 90% -> fine
        calls = []
        with patched(tr, complete=fake_complete_factory([json.dumps(FAKE_PROFILE)], calls)):
            profile = tr.analyze_student(sid)
    assert len(profile["weak_areas"]) == 1
    assert "ec2025-q14" in profile["weak_areas"][0]
    # the weak areas were in the prompt (the model does not compute them)
    assert "ec2025-q14" in calls[0]["user"]
    assert "Weak areas already identified" in calls[0]["user"]


def test_analyze_student_retry_then_success():
    with fresh_db():
        sid = make_student_with_rates("Retry A", [0.5, 0.6])
        calls = []
        replies = ["no json here", json.dumps(FAKE_PROFILE)]
        with patched(tr, complete=fake_complete_factory(replies, calls)):
            profile = tr.analyze_student(sid)
    assert len(calls) == 2
    assert calls[0]["temperature"] == 0.3 and calls[1]["temperature"] == 0.15
    assert profile["current_level"] == FAKE_PROFILE["current_level"]


def test_analyze_student_llm_failure_raises():
    with fresh_db():
        sid = make_student_with_rates("Boom", [0.5, 0.6])
        calls = []
        with patched(tr, complete=fake_complete_factory([RuntimeError("boom")], calls)):
            try:
                tr.analyze_student(sid)
            except RuntimeError as exc:
                assert "failed" in str(exc)
            else:
                raise AssertionError("expected RuntimeError when the LLM fails")


def test_analyze_student_unknown_student_raises():
    with fresh_db():
        try:
            tr.analyze_student(999999)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for an unknown student id")


# --------------------------------------------------------------------------
# runner (python3 tests/test_students.py)
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
