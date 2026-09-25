#!/usr/bin/env python3
"""
CoachAI - agents/student_coach.py test suite (Phase 6a practice + Q&A).

Runs both ways:

    python3 tests/test_student_coach.py
    python3 -m pytest tests/test_student_coach.py

NO real LLM calls and NO real RAG calls: complete() and retrieve_context()
are monkeypatched per test (plain setattr via the `patched` context manager,
so the file also runs without pytest fixtures). Covers: prompt assembly
(dot points, weak areas, retrieved docs, language, count), JSON parsing
(incl. fenced output and one retry on invalid JSON), the returned practice
set contract (structure, marks clamp, criteria coercion, count trim),
empty-input defence, LLM-failure behaviour, and the Q&A contract
(answer/note/sources; sources come from the retrieved docs only).
"""
import json
import os
import sys
import traceback
from contextlib import contextmanager

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents import student_coach as sc  # noqa: E402

DOT_A = "Explain how the user interface (UI) impacts on the user experience (UX)"
DOT_B = "Apply design thinking to develop a front-end, web-based interactive media system"
WEAK_A = "Q03: 42% average over 3 attempt(s)"
WEAK_B = "Q07: 55% average over 2 attempt(s)"

FAKE_PRACTICE = {
    "questions": [
        {
            "question": "A local museum wants a booking page. Explain how two UI "
                        "design choices could improve the user experience for "
                        "first-time visitors.",
            "marks": 4,
            "criteria": [
                "Names two distinct UI design choices",
                "Explains the effect of each choice on first-time visitors",
                "Uses correct UX and UI terminology",
            ],
            "hint": "Start from what a first-time visitor needs to see first.",
        },
        {
            "question": "Compare lossy and lossless compression for a student "
                        "podcast that streams online.",
            "marks": 6,
            "criteria": [
                "Describes both compression types",
                "Compares them on file size and quality",
                "Justifies a choice for streaming",
            ],
            "hint": "Think about what streaming does to audio quality.",
        },
        {
            "question": "Describe one way a project manager could use a Kanban "
                        "board during an interactive media build.",
            "marks": 3,
            "criteria": ["Describes the board", "Links it to project progress"],
            "hint": "Columns show stages of work.",
        },
        {
            "question": "Evaluate the impact of data visualisation choices on a "
                        "published data journalism piece.",
            "marks": 5,
            "criteria": ["Judgement stated", "Evidence from visualisation design"],
            "hint": "",
        },
    ]
}

FAKE_ANSWER = {
    "answer": "Lossy compression permanently discards some audio detail so the file "
              "streams with less bandwidth. The course material explains that this "
              "is a trade-off between file size and quality.",
    "note": "In the syllabus, lossy compression appears in the capture and store "
            "content group.",
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

@contextmanager
def patched(**attrs):
    """Temporarily replace module attributes on student_coach (save + restore)."""
    saved = {k: getattr(sc, k) for k in attrs}
    for k, v in attrs.items():
        setattr(sc, k, v)
    try:
        yield sc
    finally:
        for k, v in saved.items():
            setattr(sc, k, v)


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

def test_practice_prompt_contains_dots_meta_and_docs():
    system, user = sc.build_practice_prompt(
        [DOT_A, DOT_B], [], "Year 11", 3, "en",
        [{"text": "TSR chunk on UX", "source": "tsr.pdf"}],
    )
    # every ticked dot point must be in the prompt, numbered
    assert "1. " + DOT_A in user and "2. " + DOT_B in user
    # request metadata
    assert "Year: Year 11" in user
    assert "Questions requested: 3" in user
    # retrieved grounding
    assert "TSR chunk on UX" in user and "tsr.pdf" in user
    # system role + strict output contract
    assert "HSC Enterprise Computing teacher" in system
    assert "JSON" in system and "questions" in system and "hint" in system
    # language instruction
    assert "English" in user


def test_practice_prompt_weak_areas_only():
    _, user = sc.build_practice_prompt([], [WEAK_A, WEAK_B], "Year 12", 2, "en", [])
    assert WEAK_A in user and WEAK_B in user
    assert "weak areas" in user.lower()
    # no dot points supplied -> explicitly marked as absent
    assert "(none supplied" in user
    assert "No TSR context retrieved" in user


def test_practice_prompt_dedupes_weak_areas_against_dots():
    _, user = sc.build_practice_prompt([DOT_A], [DOT_A, WEAK_A], "Year 11", 1, "en", [])
    assert user.count(DOT_A) == 1          # dot point section only, not repeated as weak


def test_practice_prompt_language_zh():
    _, user = sc.build_practice_prompt([DOT_A], [], "Year 11", 1, "zh", [])
    assert "Simplified Chinese" in user


# --------------------------------------------------------------------------
# generate_practice with a mocked LLM
# --------------------------------------------------------------------------

def test_generate_practice_structure_and_focus():
    calls, rag_calls = [], []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_PRACTICE)], calls),
                 retrieve_context=fake_retrieve_factory(
                     [{"text": "TSR UI material", "source": "tsr.pdf",
                       "topic": "interactive media", "score": 0.8}], rag_calls)):
        out = sc.generate_practice([DOT_A, DOT_B], year="Year 11", count=4)
    assert set(out) == {"questions", "focus"}
    assert len(calls) == 1 and len(rag_calls) == 1
    # RAG query built from the focus items
    assert DOT_A[:40] in rag_calls[0]["query"]
    assert out["focus"] == [DOT_A, DOT_B]
    assert len(out["questions"]) == 4
    for q in out["questions"]:
        assert set(q) == {"question", "marks", "criteria", "hint"}
        assert isinstance(q["question"], str) and q["question"]
        assert isinstance(q["marks"], int) and 1 <= q["marks"] <= 10
        assert isinstance(q["criteria"], list)
        assert all(isinstance(c, str) and c for c in q["criteria"])
        assert isinstance(q["hint"], str)
    # the prompt really carried the selection, count, docs and language
    sent = calls[0]["user"]
    assert DOT_A in sent and DOT_B in sent and "1. " + DOT_A in sent
    assert "Questions requested: 4" in sent
    assert "TSR UI material" in sent and "tsr.pdf" in sent
    assert "English" in sent


def test_generate_practice_uses_weak_areas_when_no_dots():
    calls, rag_calls = [], []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_PRACTICE)], calls),
                 retrieve_context=fake_retrieve_factory([], rag_calls)):
        out = sc.generate_practice(weak_areas=[WEAK_A, WEAK_B], count=2)
    assert out["focus"] == [WEAK_A, WEAK_B]
    assert len(out["questions"]) == 2          # trimmed to the requested count
    assert WEAK_A[:20] in rag_calls[0]["query"]
    sent = calls[0]["user"]
    assert WEAK_A in sent and "(none supplied" in sent


def test_generate_practice_combines_and_dedupes_focus():
    calls = []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_PRACTICE)], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        out = sc.generate_practice(
            [{"code": "X1", "text": DOT_A}, DOT_A, "   "],
            weak_areas=[DOT_A, WEAK_A],
            count=1,
        )
    assert out["focus"] == [DOT_A, WEAK_A]
    assert len(out["questions"]) == 1


def test_generate_practice_clamps_count_to_range():
    calls = []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_PRACTICE)], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        sc.generate_practice([DOT_A], count=99)
        sc.generate_practice([DOT_A], count=0)
        sc.generate_practice([DOT_A], count="not a number")  # type: ignore[arg-type]
    assert "Questions requested: 5" in calls[0]["user"]
    assert "Questions requested: 1" in calls[1]["user"]
    assert "Questions requested: 3" in calls[2]["user"]   # fallback default


def test_question_normalisation_clamps_and_drops_invalid():
    calls = []
    messy = {"questions": [
        {"question": "Q one", "marks": 99, "criteria": "A\nB", "hint": "h"},
        {"question": "Q two", "marks": "not-a-number", "criteria": ["C"], "hint": ""},
        "not a dict",
        {"question": "   ", "marks": 4},
        {"question": "Q three", "marks": 3.9, "criteria": ["D", "  ", "E"], "hint": "  "},
    ]}
    with patched(complete=fake_complete_factory([json.dumps(messy)], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        out = sc.generate_practice([DOT_A], count=5)
    assert [q["marks"] for q in out["questions"]] == [10, 3]
    assert out["questions"][0]["criteria"] == ["A", "B"]   # string split on lines
    assert out["questions"][1]["criteria"] == ["D", "E"]   # blanks dropped
    assert out["questions"][1]["hint"] == ""


def test_generate_practice_retries_once_on_bad_json():
    calls = []
    replies = ["I am afraid I cannot help with that.", json.dumps(FAKE_PRACTICE)]
    with patched(complete=fake_complete_factory(replies, calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        out = sc.generate_practice([DOT_A], count=1)
    assert len(calls) == 2                       # first parse failed, retried once
    assert "not valid JSON" in calls[1]["user"]  # retry prompt is stricter
    assert calls[1]["temperature"] == 0.3
    assert len(out["questions"]) == 1


def test_generate_practice_llm_failure_raises_runtime_error():
    calls = []
    with patched(complete=fake_complete_factory([RuntimeError("boom")], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        try:
            sc.generate_practice([DOT_A])
        except RuntimeError as exc:
            assert "failed" in str(exc)
        else:
            raise AssertionError("expected RuntimeError when the LLM fails")


def test_generate_practice_fenced_json_is_parsed():
    calls = []
    fenced = "```json\n" + json.dumps(FAKE_PRACTICE) + "\n```"
    with patched(complete=fake_complete_factory([fenced], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        out = sc.generate_practice([DOT_A], count=4)
    assert out["questions"][0]["marks"] == 4


def test_generate_practice_empty_inputs_raise_value_error():
    for dots, weak in ((None, None), ([], []), (["  "], None), (None, [" "]), ([{}], [])):
        try:
            sc.generate_practice(dots, weak, retrieved_docs=[])
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {dots!r} / {weak!r}")


# --------------------------------------------------------------------------
# answer_question with a mocked LLM
# --------------------------------------------------------------------------

def test_answer_prompt_contains_question_context_and_docs():
    system, user = sc.build_answer_prompt(
        "Why is lossy compression used for live streaming?",
        "I just got Q4 wrong about compression.",
        "Year 12", "en",
        [{"text": "TSR compression notes", "source": "tsr.pdf"}],
    )
    assert "Why is lossy compression used for live streaming?" in user
    assert "I just got Q4 wrong about compression." in user
    assert "Year level: Year 12" in user
    assert "TSR compression notes" in user and "tsr.pdf" in user
    # repository-of-truth framing on the system role
    assert "repository of truth" in system
    assert "English" in user


def test_answer_prompt_without_docs_states_absence():
    _, user = sc.build_answer_prompt("What is an inference engine?", "", "Year 11", "en", [])
    assert "No NESA / TSR material retrieved" in user
    assert "does not cover" in user      # explicit no-fabrication instruction


def test_answer_question_structure_and_deduped_sources():
    calls, rag_calls = [], []
    docs = [
        {"text": "d1", "source": "tsr.pdf"},
        {"text": "d2", "source": "tsr.pdf"},
        {"text": "d3", "source": "extra.md"},
        {"text": "d4", "source": "?"},
    ]
    with patched(complete=fake_complete_factory([json.dumps(FAKE_ANSWER)], calls),
                 retrieve_context=fake_retrieve_factory(docs, rag_calls)):
        out = sc.answer_question("Why is lossy compression used for streaming?",
                                 context_note="I got Q4 wrong.")
    assert set(out) == {"answer", "sources", "note"}
    assert out["answer"].startswith("Lossy compression")
    assert out["note"]
    # sources come from the retrieved docs only: deduped, order kept, "?" skipped
    assert out["sources"] == ["tsr.pdf", "extra.md"]
    assert len(calls) == 1 and len(rag_calls) == 1
    assert rag_calls[0]["query"] == "Why is lossy compression used for streaming?"
    assert "I got Q4 wrong." in calls[0]["user"]


def test_answer_question_without_docs_returns_empty_sources():
    calls, rag_calls = [], []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_ANSWER)], calls),
                 retrieve_context=fake_retrieve_factory([], rag_calls)):
        out = sc.answer_question("A question", retrieved_docs=[])
    assert rag_calls == []                       # caller supplied docs: no retrieval
    assert out["sources"] == []
    assert "No NESA / TSR material retrieved" in calls[0]["user"]


def test_answer_question_retries_once_on_bad_json():
    calls = []
    replies = ["not json at all", json.dumps(FAKE_ANSWER)]
    with patched(complete=fake_complete_factory(replies, calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        out = sc.answer_question("Q?", retrieved_docs=[])
    assert len(calls) == 2
    assert "not valid JSON" in calls[1]["user"]
    assert calls[1]["temperature"] == 0.15
    assert out["answer"].startswith("Lossy")


def test_answer_question_missing_answer_field_fails_after_retry():
    calls = []
    with patched(complete=fake_complete_factory([json.dumps({"note": "only a note"})], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        try:
            sc.answer_question("Q?", retrieved_docs=[])
        except RuntimeError as exc:
            assert "failed" in str(exc)
        else:
            raise AssertionError("expected RuntimeError when the answer field is missing")
    assert len(calls) == 2


def test_answer_note_is_optional():
    calls = []
    with patched(complete=fake_complete_factory([json.dumps({"answer": "Plain answer."})], calls),
                 retrieve_context=fake_retrieve_factory([], [])):
        out = sc.answer_question("Q?", retrieved_docs=[])
    assert out["answer"] == "Plain answer." and out["note"] == ""


def test_answer_question_empty_raises_value_error():
    for bad in ("", "   ", None):
        try:
            sc.answer_question(bad, retrieved_docs=[])  # type: ignore[arg-type]
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")


# --------------------------------------------------------------------------
# runner (python3 tests/test_student_coach.py)
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
