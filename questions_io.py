#!/usr/bin/env python3
"""
CoachAI — shared question-bank IO (official bank + teacher-authored customs).

    data/questions.json         official HSC bank (read-only for the app)
    data/custom_questions.json  questions saved through the Gradio form

Both files share one wrapper shape:

    {"subject": str, "source": str, "questions": [ {question}, ... ]}

Stdlib-only and Gradio-free so the marking engine (graphs/mark_graph.py)
and the UI (app.py) can share the exact same loading/merging logic.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CUSTOM_FILE = "custom_questions.json"

CUSTOM_SUBJECT = "Enterprise Computing"
CUSTOM_SOURCE = "Teacher-authored custom questions (CoachAI)"

# A band prefix inside a criteria line: "3 marks: ..." / "3: ..." / "1-2 - ..."
_BAND_PREFIX_RE = re.compile(
    r"^\s*(\d{1,2}(?:\s*[–—-]\s*\d{1,2})?)\s*(?:marks?|分)?\s*[:：.\-–—]\s*(.+)$",
    re.IGNORECASE,
)


# --------------------------------------------------------------------- reading

def read_questions_file(path) -> list[dict]:
    """Return the questions list of one bank file.

    Accepts both {"questions": [...]} wrappers and bare lists. Missing or
    corrupt files yield [] (logged to stderr) so callers never crash.
    """
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError as exc:
        print(f"[questions_io] cannot read {path}: {exc}", file=sys.stderr)
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"[questions_io] invalid JSON in {path}: {exc}", file=sys.stderr)
        return []
    if isinstance(data, dict):
        questions = data.get("questions", [])
    elif isinstance(data, list):
        questions = data
    else:
        questions = []
    return [q for q in questions if isinstance(q, dict)]


def load_all_questions(paths) -> list[dict]:
    """Merge question files in the given order (custom files listed last).

    Duplicate ids are dropped keeping the FIRST occurrence, so the official
    bank wins and the question dropdown can never show the same id twice.
    """
    merged: list[dict] = []
    seen: set = set()
    for path in paths:
        for q in read_questions_file(path):
            qid = q.get("id")
            if qid:
                if qid in seen:
                    continue
                seen.add(qid)
            merged.append(q)
    return merged


# --------------------------------------------------------------------- writing

def next_custom_id(existing_ids) -> str:
    """Return the first free 'custom-N' id (N = 1, 2, 3, ...)."""
    used = {str(i) for i in existing_ids if i}
    n = 1
    while f"custom-{n}" in used:
        n += 1
    return f"custom-{n}"


def parse_marking_criteria(text: str | None, marks=None) -> list[dict]:
    """Turn the teacher's free-text criteria into marking_guidelines entries.

    One entry per non-empty line. A leading band ("3 marks: ...", "3: ...",
    "1-2 - ...") is captured as the band; lines without one inherit the
    question's maximum mark so the rubric never renders a blank band.
    """
    lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    if not lines:
        return []
    fallback = str(marks).strip() if marks not in (None, "") else "?"
    out = []
    for line in lines:
        m = _BAND_PREFIX_RE.match(line)
        if m:
            out.append({"band": m.group(1).strip(), "criteria": m.group(2).strip()})
        else:
            out.append({"band": fallback, "criteria": line})
    return out


def validate_custom_question(question: dict) -> list[str]:
    """Return human-readable problems with a custom question ([] => valid)."""
    if not isinstance(question, dict):
        return ["question must be a dict"]
    errors = []
    if not str(question.get("text") or "").strip():
        errors.append("question text is required")
    marks = question.get("marks")
    if marks in (None, ""):
        errors.append("marks is required")
    else:
        try:
            value = float(marks)
        except (TypeError, ValueError):
            errors.append("marks must be a number")
        else:
            if value <= 0 or not value.is_integer():
                errors.append("marks must be a positive whole number")
    if not (question.get("marking_guidelines") or []):
        errors.append("marking criteria is required")
    return errors


def save_custom_question(data_dir, question: dict) -> str:
    """Validate and append a teacher-authored question; return its new id.

    `question` accepts the raw Gradio form fields (text, marks, criteria,
    sample_answer) or a ready question dict (with marking_guidelines).
    The file keeps the same {"subject", "source", "questions": [...]}
    wrapper as data/questions.json and is always written with
    ensure_ascii=False so mixed Chinese/English text stays readable.

    Raises ValueError (and writes nothing) when validation fails.
    """
    data_dir = Path(data_dir)
    record = dict(question or {})

    # Free-text "criteria" form field => NESA-style marking_guidelines list.
    if not record.get("marking_guidelines"):
        record["marking_guidelines"] = parse_marking_criteria(
            record.get("criteria", ""), record.get("marks")
        )
    record.pop("criteria", None)

    errors = validate_custom_question(record)
    if errors:
        raise ValueError("invalid custom question: " + "; ".join(errors))

    record["text"] = str(record["text"]).strip()
    record["marks"] = int(float(record["marks"]))

    # Optional single sample answer -> sample_answers list (bank's key name).
    sample = str(record.pop("sample_answer", "") or "").strip()
    if sample and not record.get("sample_answers"):
        record["sample_answers"] = [sample]
    record.setdefault("sample_answers", [])
    record.setdefault("topics", ["custom"])

    # Ids must stay unique across the official bank and the custom file.
    custom_path = data_dir / CUSTOM_FILE
    existing_ids = [q.get("id") for q in read_questions_file(data_dir / "questions.json")]
    existing_ids += [q.get("id") for q in read_questions_file(custom_path)]
    qid = next_custom_id(existing_ids)

    clean = {
        "id": qid,
        "text": record["text"],
        "marks": record["marks"],
        "marking_guidelines": record["marking_guidelines"],
        "sample_answers": record.get("sample_answers", []),
        "topics": record.get("topics", ["custom"]),
    }
    # Keep any extra teacher-provided fields (never clobber id/schema keys).
    for key, value in record.items():
        if key not in clean and key != "id":
            clean[key] = value

    questions = read_questions_file(custom_path)
    questions.append(clean)
    payload = {"subject": CUSTOM_SUBJECT, "source": CUSTOM_SOURCE, "questions": questions}

    data_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = custom_path.parent / (custom_path.name + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    tmp_path.replace(custom_path)  # atomic swap: readers never see a half file
    return qid


if __name__ == "__main__":  # quick manual check
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        qid = save_custom_question(td, {
            "text": "Describe how a feedforward neural network learns. 描述神经网络的学习过程。",
            "marks": 4,
            "criteria": "4 marks: Explains backpropagation clearly\n2 marks: Outlines training steps\n1 mark: Provides some relevant information",
        })
        print("saved:", qid)
        print((Path(td) / CUSTOM_FILE).read_text(encoding="utf-8"))
