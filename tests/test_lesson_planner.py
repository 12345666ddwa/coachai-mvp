#!/usr/bin/env python3
"""
CoachAI — agents/lesson_planner.py test suite (Phase 4 lesson generation).

Runs both ways:

    python3 tests/test_lesson_planner.py
    python3 -m pytest tests/test_lesson_planner.py

NO real LLM calls and NO real RAG calls: complete() and retrieve_context()
are monkeypatched per test (plain setattr, so the file also runs without
pytest fixtures). Covers: prompt assembly (ticked dot points + reference
material + retrieved docs + language), JSON parsing (incl. fenced output and
one retry on invalid JSON), the returned plan contract, empty-selection
validation, LLM-failure behaviour, and the pure syllabus/UI-linkage helpers.
"""
import json
import os
import sys
import traceback
from contextlib import contextmanager

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents import lesson_planner as lp  # noqa: E402

DOT_A = "Apply design thinking to develop a front-end, web-based interactive media system"
DOT_B = "Develop and publish an interactive work of data journalism"
REF_TEXT = "Week 3 slides: design thinking starts with empathy interviews. Assessment is a portfolio."

FAKE_PLAN = {
    "title": "Design thinking in interactive media",
    "objectives": [
        "Explain the five stages of the design thinking process",
        "Model an empathy interview plan for a given user group",
        "Construct a low-fidelity prototype for a web-based artefact",
    ],
    "flow": [
        {"time": "0–10", "activity": "Hook: a bad interface",
         "detail": "Show a deliberately unusable page; students list the failures."},
        {"time": "10–30", "activity": "Direct instruction",
         "detail": "Five design thinking stages with the week 3 slides."},
        {"time": "30–50", "activity": "Group task",
         "detail": "Groups draft an empathy interview plan and sketch a prototype."},
        {"time": "50–60", "activity": "Debrief and exit ticket",
         "detail": "One question: which stage matters most for your user group, and why?"},
    ],
    "assessment": "Exit ticket sorted into needs reteach / on track / ready for extension.",
    # Deliberately NOT equal to the selection: normalisation must force it back.
    "alignment": ["Some model-written summary of coverage"],
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

@contextmanager
def patched(**attrs):
    """Temporarily replace module attributes on lesson_planner (save + restore)."""
    saved = {k: getattr(lp, k) for k in attrs}
    for k, v in attrs.items():
        setattr(lp, k, v)
    try:
        yield lp
    finally:
        for k, v in saved.items():
            setattr(lp, k, v)


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


def fake_retrieve_factory(docs, calls):
    def _fake(query, k=4):
        calls.append({"query": query, "k": k})
        return docs
    return _fake


# --------------------------------------------------------------------------
# prompt assembly
# --------------------------------------------------------------------------

def test_prompt_contains_dot_points_and_reference():
    system, user = lp.build_lesson_prompt(
        [DOT_A, DOT_B], REF_TEXT, "Year 11", 60,
        "Interactive media and the user experience", "en", [],
    )
    # every ticked dot point must be in the prompt, numbered
    assert DOT_A in user and DOT_B in user
    assert "1. " + DOT_A in user and "2. " + DOT_B in user
    # reference material kept as the content baseline
    assert REF_TEXT in user
    assert "content baseline" in user
    # request metadata
    assert "Year: Year 11" in user
    assert "60 minutes" in user
    assert "Interactive media and the user experience" in user
    # system role + strict output contract
    assert "HSC Enterprise Computing teacher" in system
    assert "JSON" in system and "alignment" in system
    # language instruction
    assert "English" in user


def test_prompt_without_reference_marks_it_absent():
    _, user = lp.build_lesson_prompt([DOT_A], "", "Year 11", 45, "M", "en",
                                     [{"text": "TSR chunk one", "source": "tsr.pdf"}])
    assert "No reference material provided" in user
    assert "TSR chunk one" in user and "tsr.pdf" in user


def test_empty_retrieved_docs_noted_in_prompt():
    _, user = lp.build_lesson_prompt([DOT_A], "", "Y", 60, "M", "en", [])
    assert "No TSR context retrieved" in user


def test_prompt_language_zh():
    _, user = lp.build_lesson_prompt([DOT_A], "第3周课件", "Year 12", 60, "M", "zh", [])
    assert "Simplified Chinese" in user


# --------------------------------------------------------------------------
# generation with a mocked LLM
# --------------------------------------------------------------------------

def test_generate_plan_structure_and_alignment():
    calls, rag_calls = [], []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_PLAN)], calls),
                 retrieve_context=fake_retrieve_factory(
                     [{"text": "TSR design thinking material", "source": "tsr.pdf",
                       "topic": "interactive media", "score": 0.8}], rag_calls)):
        plan = lp.generate_lesson_plan([DOT_A, DOT_B], reference_text=REF_TEXT,
                                       year="Year 11", duration_min=60,
                                       focus_area="Interactive media and the user experience")
    # one LLM call; query came from focus area + dot points
    assert len(calls) == 1 and len(rag_calls) == 1
    assert DOT_A[:40] in rag_calls[0]["query"]
    # structure fields all present
    for key in ("title", "year", "duration_min", "focus_area", "objectives",
                "flow", "assessment", "alignment", "generated_with"):
        assert key in plan, f"missing key: {key}"
    assert plan["year"] == "Year 11" and plan["duration_min"] == 60
    assert plan["focus_area"] == "Interactive media and the user experience"
    assert len(plan["objectives"]) >= 3
    assert all(isinstance(o, str) and o for o in plan["objectives"])
    assert 4 <= len(plan["flow"]) <= 6
    for seg in plan["flow"]:
        assert set(seg) == {"time", "activity", "detail"}
    # alignment is forced to the teacher's selection
    assert plan["alignment"] == [DOT_A, DOT_B]
    # generation provenance
    assert plan["generated_with"] == {"reference_len": len(REF_TEXT), "rag_used": True}
    # the prompt really carried the selection, reference and retrieved context
    sent = calls[0]["user"]
    assert DOT_A in sent and DOT_B in sent and REF_TEXT in sent
    assert "TSR design thinking material" in sent
    assert "English" in sent


def test_generate_uses_inferred_chinese_language():
    calls = []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_PLAN)], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        lp.generate_lesson_plan(["描述数据分析的基本流程"], reference_text="第三周课件：数据分析流程",
                                year="Year 12", focus_area="Data science")
    assert "Simplified Chinese" in calls[0]["user"]


def test_generate_accepts_pre_fetched_docs_without_rag():
    calls, rag_calls = [], []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_PLAN)], calls),
                 retrieve_context=fake_retrieve_factory([], rag_calls)):
        plan = lp.generate_lesson_plan([DOT_A], retrieved_docs=[])
    assert rag_calls == []                      # caller supplied docs: no retrieval
    assert plan["generated_with"]["rag_used"] is False
    assert "No TSR context retrieved" in calls[0]["user"]


def test_generate_dedupes_and_accepts_dict_dot_points():
    calls = []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_PLAN)], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        plan = lp.generate_lesson_plan(
            [{"code": "X1", "text": DOT_A}, DOT_A, "   "],
            retrieved_docs=[],
        )
    assert plan["alignment"] == [DOT_A]


# --------------------------------------------------------------------------
# validation / failure behaviour
# --------------------------------------------------------------------------

def test_empty_dot_points_raises_value_error():
    for bad in ([], None, ["   "], [""]):
        try:
            lp.generate_lesson_plan(bad, retrieved_docs=[])  # type: ignore[arg-type]
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")


def test_retry_on_invalid_json():
    calls = []
    replies = ["I am afraid I cannot do that.", json.dumps(FAKE_PLAN)]
    with patched(complete=fake_complete_factory(replies, calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        plan = lp.generate_lesson_plan([DOT_A], retrieved_docs=[])
    assert len(calls) == 2                       # first parse failed, retried once
    assert "not valid JSON" in calls[1]["user"]  # retry prompt is stricter
    assert calls[1]["temperature"] == 0.2
    assert plan["title"] == FAKE_PLAN["title"]


def test_thin_json_also_triggers_retry():
    """Valid JSON but no objectives -> validation error -> retry."""
    calls = []
    replies = [json.dumps({"title": "T", "flow": []}), json.dumps(FAKE_PLAN)]
    with patched(complete=fake_complete_factory(replies, calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        plan = lp.generate_lesson_plan([DOT_A], retrieved_docs=[])
    assert len(calls) == 2 and plan["objectives"]


def test_llm_failure_raises_runtime_error():
    calls = []
    with patched(complete=fake_complete_factory([RuntimeError("boom")], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        try:
            lp.generate_lesson_plan([DOT_A], retrieved_docs=[])
        except RuntimeError as exc:
            assert "failed" in str(exc)
        else:
            raise AssertionError("expected RuntimeError when the LLM fails")


def test_fenced_json_is_parsed():
    calls = []
    fenced = "```json\n" + json.dumps(FAKE_PLAN) + "\n```"
    with patched(complete=fake_complete_factory([fenced], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        plan = lp.generate_lesson_plan([DOT_B], retrieved_docs=[])
    assert plan["title"] == FAKE_PLAN["title"]


def test_flow_normalisation_accepts_loose_entries():
    calls = []
    loose = dict(FAKE_PLAN)
    loose["flow"] = [
        "Warm-up discussion",
        {"time": "10–30", "activity": "Instruction"},              # no detail
        {"time": "30–60", "detail": "Students build the thing"},   # no activity
        {"time": "60–70"},                                         # empty: dropped
    ]
    with patched(complete=fake_complete_factory([json.dumps(loose)], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        plan = lp.generate_lesson_plan([DOT_A], retrieved_docs=[])
    assert len(plan["flow"]) == 3
    assert plan["flow"][0]["time"] == "?"            # string entry keeps shape
    assert plan["flow"][1]["detail"] == ""           # missing detail tolerated
    assert plan["flow"][2]["activity"] == "Students build the thing"


# --------------------------------------------------------------------------
# pure helpers (syllabus data + language inference)
# --------------------------------------------------------------------------

def test_infer_lang():
    assert lp.infer_lang("") == "en"
    assert lp.infer_lang(DOT_A) == "en"
    assert lp.infer_lang("第三周的课程材料，包含设计思维的全部内容。") == "zh"
    # mostly-Chinese material with a couple of English terms still means zh
    assert lp.infer_lang("讨论 design thinking 与 UX 的关系，并完成课堂练习。") == "zh"
    # English material with one Chinese word stays English
    assert lp.infer_lang("Design thinking and UX in interactive media " * 2 + "数据") == "en"


def test_syllabus_helpers_real_data():
    syl = lp.load_syllabus()
    y11 = lp.list_modules(syl, "Year 11")
    y12 = lp.list_modules(syl, "Year 12")
    assert y11 == ["Interactive media and the user experience",
                   "Principles of cybersecurity",
                   "Networking systems and social computing"]
    assert y12 == ["Data science", "Data visualisation", "Intelligent systems",
                   "Enterprise project"]
    assert lp.list_modules(syl, "Year 13") == []

    dps = lp.module_dot_points(syl, "Year 12", "Data science")
    assert len(dps) >= 10
    assert all(d["code"] and d["text"] and d["group"] for d in dps)
    assert lp.dot_point_texts(syl, "Year 12", "Data science") == [d["text"] for d in dps]
    assert lp.module_dot_points(syl, "Year 12", "No such module") == []

    total = sum(len(lp.module_dot_points(syl, y, m))
                for y in ("Year 11", "Year 12")
                for m in lp.list_modules(syl, y))
    assert total == 180   # NESA dataset size pinned by the Phase 0 extraction


# --------------------------------------------------------------------------
# runner (python3 tests/test_lesson_planner.py)
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
