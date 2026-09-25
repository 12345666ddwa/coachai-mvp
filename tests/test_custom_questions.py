#!/usr/bin/env python3
"""
CoachAI — tests for questions_io (teacher-authored custom questions).

Runs both ways:

    python3 tests/test_custom_questions.py
    python3 -m pytest tests/test_custom_questions.py

Covers: save round-trip with mixed Chinese/English text (ensure_ascii=False),
auto id assignment (custom-1, custom-2, ...; collision-safe against the
official bank), merge order (official first, custom last), duplicate-id and
corrupt/missing-file handling, criteria band parsing, and form validation.
NO LLM calls and NO Gradio import — pure stdlib behaviour only.
"""
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from questions_io import (  # noqa: E402
    CUSTOM_FILE,
    load_all_questions,
    next_custom_id,
    parse_marking_criteria,
    read_questions_file,
    save_custom_question,
    validate_custom_question,
)

# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

OFFICIAL_Q = {
    "id": "ec2025-q11",
    "text": "Which of the following is TRUE about forward chaining?",
    "marks": 2,
    "marking_guidelines": [
        {"band": "2", "criteria": "Identifies true or false correctly for all FIVE checkboxes"}
    ],
    "sample_answers": [],
    "topics": ["intelligent systems"],
}

OTHER_Q = {
    "id": "custom-1",
    "text": "A duplicate id living in the custom file.",
    "marks": 1,
    "marking_guidelines": [{"band": "1", "criteria": "Provides some relevant information"}],
    "sample_answers": [],
    "topics": [],
}

# Exactly what the Gradio form sends: text / marks / criteria / sample_answer
CUSTOM_FORM = {
    "text": "Explain how a data warehouse supports decision-making.\n解释数据仓库如何支持决策。",
    "marks": 3,
    "criteria": ("3 marks: Explains how the data warehouse supports decision-making\n"
                 "2 marks: Outlines one feature\n"
                 "1 mark: Provides some relevant information"),
    "sample_answer": "A data warehouse consolidates data from multiple sources ...",
}


def _bank(questions, subject="Enterprise Computing"):
    return {"subject": subject, "source": "unit-test", "questions": questions}


def _write(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------

def test_save_roundtrip_mixed_language():
    """Saving writes questions.json-shaped JSON with Chinese kept literal."""
    with tempfile.TemporaryDirectory() as td:
        qid = save_custom_question(td, CUSTOM_FORM)
        assert qid == "custom-1"

        path = Path(td) / CUSTOM_FILE
        assert path.exists()
        raw = path.read_text(encoding="utf-8")
        # ensure_ascii=False: the Chinese must be stored literally, not escaped
        assert "解释数据仓库如何支持决策。" in raw
        assert "\\u89e3" not in raw

        payload = json.loads(raw)
        assert set(payload) >= {"subject", "source", "questions"}
        assert len(payload["questions"]) == 1
        q = payload["questions"][0]
        assert q["id"] == "custom-1"
        assert q["marks"] == 3
        assert q["sample_answers"] == [CUSTOM_FORM["sample_answer"]]
        assert [g["band"] for g in q["marking_guidelines"]] == ["3", "2", "1"]
        assert q["marking_guidelines"][0]["criteria"].startswith("Explains how")
        # read-back through the loader gives the identical record
        assert read_questions_file(path)[0] == q


def test_ids_increment_and_merge_order():
    """custom-1..N are assigned in order; merge puts official first."""
    with tempfile.TemporaryDirectory() as td:
        official = Path(td) / "questions.json"
        _write(official, _bank([OFFICIAL_Q]))

        ids = [save_custom_question(td, {**CUSTOM_FORM, "text": f"Question {n}"})
               for n in (1, 2, 3)]
        assert ids == ["custom-1", "custom-2", "custom-3"]

        merged = load_all_questions([official, Path(td) / CUSTOM_FILE])
        merged_ids = [q["id"] for q in merged]
        assert merged_ids == ["ec2025-q11", "custom-1", "custom-2", "custom-3"]
        assert len(merged_ids) == len(set(merged_ids))  # ids stay unique
        assert merged[-1]["text"] == "Question 3"       # custom appended last


def test_id_collision_with_official_bank():
    """A custom-N id already used by the official bank is skipped."""
    with tempfile.TemporaryDirectory() as td:
        _write(Path(td) / "questions.json", _bank([{**OFFICIAL_Q, "id": "custom-1"}]))
        assert save_custom_question(td, CUSTOM_FORM) == "custom-2"
        assert save_custom_question(td, CUSTOM_FORM) == "custom-3"


def test_missing_empty_and_fresh_files():
    """Missing / empty custom files never break loading; save creates them."""
    with tempfile.TemporaryDirectory() as td:
        official = Path(td) / "questions.json"
        custom = Path(td) / CUSTOM_FILE
        _write(official, _bank([OFFICIAL_Q]))

        # custom file absent -> official questions only
        assert [q["id"] for q in load_all_questions([official, custom])] == ["ec2025-q11"]

        # custom file present but empty -> still fine
        _write(custom, _bank([]))
        assert [q["id"] for q in load_all_questions([official, custom])] == ["ec2025-q11"]

        # both files absent -> []
        assert load_all_questions([Path(td) / "nope.json", custom]) == []

        # saving into a fresh directory creates the custom file
        fresh = Path(td) / "fresh"
        assert save_custom_question(fresh, CUSTOM_FORM) == "custom-1"
        assert (fresh / CUSTOM_FILE).exists()
        assert [q["id"] for q in load_all_questions([fresh / CUSTOM_FILE])] == ["custom-1"]


def test_corrupt_and_duplicate_ids():
    """Corrupt JSON is skipped gracefully; duplicate ids keep the first."""
    with tempfile.TemporaryDirectory() as td:
        official = Path(td) / "questions.json"
        custom = Path(td) / CUSTOM_FILE
        _write(official, _bank([OFFICIAL_Q]))

        custom.write_text("{ definitely not json", encoding="utf-8")
        assert [q["id"] for q in load_all_questions([official, custom])] == ["ec2025-q11"]

        # duplicate id across files -> official (first) wins, custom copy dropped
        _write(custom, _bank([{**OTHER_Q, "text": "DUPLICATE"}, OTHER_Q]))
        merged = load_all_questions([official, custom])
        assert [q["id"] for q in merged] == ["ec2025-q11", "custom-1"]
        assert merged[0]["text"] == OFFICIAL_Q["text"]


def test_bare_list_shape_supported():
    """A bare JSON list (no wrapper) is accepted too."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "list.json"
        _write(p, [OFFICIAL_Q])
        assert [q["id"] for q in load_all_questions([p])] == ["ec2025-q11"]


def test_next_custom_id():
    assert next_custom_id([]) == "custom-1"
    assert next_custom_id(["ec2025-q11", "custom-1", "custom-3"]) == "custom-2"
    assert next_custom_id([None, "", "custom-1", "custom-2"]) == "custom-3"


def test_parse_marking_criteria():
    bands = parse_marking_criteria(
        "3 marks: Explains clearly\n2: Outlines\n1-2 - Identifies", 5)
    assert [(g["band"], g["criteria"]) for g in bands] == [
        ("3", "Explains clearly"), ("2", "Outlines"), ("1-2", "Identifies")]

    # unlabelled lines inherit the max mark so the rubric never shows a blank band
    plain = parse_marking_criteria("Describes how X works.\nOutlines Y.", 4)
    assert [(g["band"], g["criteria"]) for g in plain] == [
        ("4", "Describes how X works."), ("4", "Outlines Y.")]

    assert parse_marking_criteria("", 4) == []
    assert parse_marking_criteria(None, None) == []


def test_ready_made_question_dict():
    """A dict with marking_guidelines already built passes through untouched."""
    with tempfile.TemporaryDirectory() as td:
        qid = save_custom_question(td, {
            "text": "Describe ...",
            "marks": 5,
            "marking_guidelines": [{"band": "5", "criteria": "Describes all"}],
            "sample_answers": ["sample"],
            "topics": ["data science"],
        })
        q = read_questions_file(Path(td) / CUSTOM_FILE)[0]
        assert qid == "custom-1"
        assert q["marking_guidelines"] == [{"band": "5", "criteria": "Describes all"}]
        assert q["sample_answers"] == ["sample"]
        assert q["topics"] == ["data science"]


def test_validation_rejects_and_writes_nothing():
    bad_cases = [
        {"text": "   ", "marks": 2, "criteria": "has criteria"},          # blank text
        {"text": "has text", "marks": None, "criteria": "has criteria"},   # no marks
        {"text": "has text", "marks": 0, "criteria": "has criteria"},      # zero marks
        {"text": "has text", "marks": "abc", "criteria": "has criteria"},  # non-numeric
        {"text": "has text", "marks": 2.5, "criteria": "has criteria"},    # non-whole
        {"text": "has text", "marks": 2, "criteria": "   "},               # blank criteria
    ]
    with tempfile.TemporaryDirectory() as td:
        for case in bad_cases:
            try:
                save_custom_question(td, case)
            except ValueError as exc:
                assert "invalid custom question" in str(exc)
            else:
                raise AssertionError(f"expected ValueError for {case!r}")
        assert not (Path(td) / CUSTOM_FILE).exists()  # nothing was written

    errs = validate_custom_question({"text": "", "marks": "", "marking_guidelines": []})
    assert len(errs) == 3


# --------------------------------------------------------------------------
# runner (python3 tests/test_custom_questions.py)
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
