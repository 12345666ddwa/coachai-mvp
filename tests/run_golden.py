#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoachAI Golden Set auto-evaluation script
=========================================
Reads tests/golden_set.json (8 questions x 4 bands = 32 student answers with
expected marks) and calls the marking interface once per answer:

    from graphs.mark_graph import mark_answer
    result = mark_answer(question_id, student_answer) -> dict
    # Interface contract: see the top of app.py — the dict contains keys such
    # as "marks" / "max_marks"
    # Also compatible with implementations that return an int directly

AI marks vs expected marks (expected_marks) fall into three verdicts:
    exact   — identical
    ±1band  — differ by 1 mark (all 8 selected questions use 1-mark MG bands,
              so |Δ|=1 ≈ one band off)
    miss    — differ by ≥ 2 marks

Output: per-answer detail plus agreement statistics overall / by quality /
by question.

Note: if graphs.mark_graph.mark_answer is not available (interface not
implemented yet, or dependencies missing), the script automatically SKIPs
(expected behaviour; the exit code stays 0 so CI can run through first).
Once the interface is ready, just run it directly.

Usage:  python tests/run_golden.py     (run from the project root ai-coach/,
        or any cwd)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
GOLDEN_PATH = BASE_DIR / "tests" / "golden_set.json"

QUALITY_ORDER = ["excellent", "good", "weak", "borderline"]


def load_golden() -> list[dict]:
    """Load the golden set and perform basic structural validation."""
    data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    items = data.get("items")
    if not items:
        raise SystemExit("[run_golden] golden_set.json contains no items")
    for item in items:
        assert item.get("question_id") and item.get("question_text")
        assert len(item.get("answers", [])) == 4
        for a in item["answers"]:
            assert a["quality"] in QUALITY_ORDER
            assert isinstance(a["expected_marks"], int)
            assert 0 <= a["expected_marks"] <= item["marks"]
    return items


def import_grader():
    """Import the marking interface; return None if unavailable (caller handles SKIP)."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from graphs.mark_graph import mark_answer  # noqa: PLC0415
        return mark_answer
    except Exception as exc:  # noqa: BLE001 — missing interface / missing deps both count as "not ready"
        print(f"[SKIP] Marking interface graphs.mark_graph.mark_answer is unavailable: "
              f"{type(exc).__name__}: {exc}")
        print("[SKIP] This is expected behaviour (the interface is not implemented yet). "
              "Once it is (see the contract at the top of app.py), just re-run this script.")
        return None


def extract_marks(result) -> int:
    """Extract the mark from the interface return value: dict -> 'marks' key (may be int/str), or a plain int."""
    if isinstance(result, dict):
        marks = result.get("marks")
        if marks is None:
            raise ValueError(f"Return value is missing the 'marks' key: {result}")
        return int(marks)
    if isinstance(result, (int, float)):
        return int(result)
    raise ValueError(f"Cannot parse the marking return value: {result!r}")


def verdict(diff: int) -> str:
    if diff == 0:
        return "exact"
    if abs(diff) == 1:
        return "±1band"
    return "miss"


def main() -> int:
    items = load_golden()
    mark_answer = import_grader()
    if mark_answer is None:
        return 0  # SKIP is expected; not treated as failure

    # Stats containers: (total, exact, off1, miss, n_a)
    overall = [0, 0, 0, 0, 0]
    by_quality = {q: [0, 0, 0, 0, 0] for q in QUALITY_ORDER}
    by_question: dict[str, list[int]] = {}

    print(f"\n{'=' * 78}\nPer-answer comparison (interface: graphs.mark_graph.mark_answer)\n{'=' * 78}")
    for item in items:
        qid, qmarks = item["question_id"], item["marks"]
        by_question.setdefault(qid, [0, 0, 0, 0, 0])
        for ans in item["answers"]:
            quality, expected = ans["quality"], ans["expected_marks"]
            row = f"[{qid}] {quality:<10} expected={expected}"
            try:
                result = mark_answer(qid, ans["text"])
                got = extract_marks(result)
            except Exception as exc:  # noqa: BLE001 — a single failure must not abort the whole run
                got = None
                status = "SKIP"
                detail = f"{type(exc).__name__}: {exc}"
            else:
                diff = got - expected
                status = verdict(diff)
                detail = f"got={got} (Δ{diff:+d})"

            # Update stats (SKIP counts into the n_a bucket)
            for bucket in (overall, by_quality[quality], by_question[qid]):
                bucket[0] += 1
                if got is None:
                    bucket[4] += 1
                elif status == "exact":
                    bucket[1] += 1
                elif status == "±1band":
                    bucket[2] += 1
                else:
                    bucket[3] += 1
            print(f"  {row:<34} -> {status:<7} {detail}")

    def fmt(bucket: list[int]) -> str:
        total, exact, off1, miss, n_a = bucket
        graded = total - n_a
        if graded == 0:
            return f"n={total:<3} none graded"
        exact_r = 100.0 * exact / graded
        close_r = 100.0 * (exact + off1) / graded
        return (f"n={total:<3} exact={exact} ±1band={off1} miss={miss} "
                f"skip={n_a} | Exact rate={exact_r:5.1f}% ±1band rate={close_r:5.1f}%")

    print(f"\n{'=' * 78}\nSummary\n{'=' * 78}")
    print(f"[Overall] {fmt(overall)}")
    print("\nBy quality band:")
    for q in QUALITY_ORDER:
        print(f"  {q:<10} {fmt(by_quality[q])}")
    print("\nBy question:")
    for qid in by_question:
        print(f"  {qid} {fmt(by_question[qid])}")

    total, exact, off1, miss, n_a = overall
    graded = total - n_a
    if graded:
        rate = 100.0 * (exact + off1) / graded
        print(f"\nConclusion: {graded}/{total} answers graded successfully; exact+±1band overall agreement {rate:.1f}% "
              f"(exact {100.0*exact/graded:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
