#!/usr/bin/env python3
"""
CoachAI - tools/transcript_analyzer.py test suite (Phase 6b lesson review).

Runs both ways:

    python3 tests/test_transcript_analyzer.py
    python3 -m pytest tests/test_transcript_analyzer.py

NO real LLM calls and NO real faster-whisper runs: complete() is monkeypatched
per test (plain setattr via the `patched` context manager, so the file also
runs without pytest fixtures), and the whisper model is replaced by a fake
faster_whisper module injected into sys.modules. Covers: prompt assembly
(transcript, dot points, year, focus area, language, truncation), the review
contract (summary / strengths / missed / coverage / recommendations), coverage
alignment and boolean coercion, one retry on invalid JSON, empty-input
defence, and the transcribe_audio error paths (missing file, missing
dependency, decoder failure) plus its happy path against the fake model.
"""
import json
import os
import sys
import tempfile
import traceback
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools import transcript_analyzer as ta  # noqa: E402

DOT_A = ("Apply design thinking to develop a front-end, web-based interactive "
         "media system incorporating UX and UI principles")
DOT_B = "Explain how the user interface (UI) impacts on the user experience (UX)"
DOT_C = "Describe the purpose of lossy and lossless compression in media systems"

TRANSCRIPT = (
    "Welcome everyone. Today we start with design thinking: empathise, define, "
    "ideate, prototype and test. Let us apply the five stages to a booking page "
    "scenario. Now, quickly, compression also exists but that is next week."
)

FAKE_ANALYSIS = {
    "lesson_summary": ("The lesson introduced the five design thinking stages and "
                       "applied them to a booking page scenario."),
    "strengths": ["Clear worked example: the booking page walkthrough",
                  "Checked understanding with a quick verbal quiz"],
    "missed": ["Accessibility guidelines for the booking form were not explained"],
    "coverage": [
        {"dot_point": DOT_A, "covered": True,
         "evidence": "empathise, define, ideate, prototype and test"},
        {"dot_point": DOT_B, "covered": False,
         "evidence": "only named as next week's topic, never explained"},
    ],
    "recommendations": ["Model a full UX walkthrough next lesson",
                        "Add a short accessibility demonstration",
                        "Provide a prototype checklist"],
}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

@contextmanager
def patched(**attrs):
    """Temporarily replace module attributes on transcript_analyzer (save + restore)."""
    saved = {k: getattr(ta, k) for k in attrs}
    for k, v in attrs.items():
        setattr(ta, k, v)
    try:
        yield ta
    finally:
        for k, v in saved.items():
            setattr(ta, k, v)


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


@contextmanager
def fake_whisper(model_cls):
    """Install a fake faster_whisper module in sys.modules (save + restore)."""
    saved = sys.modules.get("faster_whisper", "MISSING")
    module = ModuleType("faster_whisper")
    module.WhisperModel = model_cls
    sys.modules["faster_whisper"] = module
    try:
        yield
    finally:
        if saved == "MISSING":
            sys.modules.pop("faster_whisper", None)
        else:
            sys.modules["faster_whisper"] = saved


@contextmanager
def blocked_whisper():
    """Simulate faster-whisper not being installed (None in sys.modules)."""
    saved = sys.modules.get("faster_whisper", "MISSING")
    sys.modules["faster_whisper"] = None
    try:
        yield
    finally:
        if saved == "MISSING":
            sys.modules.pop("faster_whisper", None)
        else:
            sys.modules["faster_whisper"] = saved


def fake_model_factory(segments, info, fail=False):
    """Fake WhisperModel class; records constructor + transcribe calls."""
    calls = []

    class _Model:
        def __init__(self, size, device=None, compute_type=None):
            calls.append({"size": size, "device": device, "compute_type": compute_type})

        def transcribe(self, path, **kwargs):
            calls.append({"path": path, "kwargs": kwargs})
            if fail:
                raise ValueError("decoder exploded")
            return iter(list(segments)), info

    return _Model, calls


def temp_audio_file(suffix=".m4a"):
    """Create an empty temp file that stands in for a recording."""
    handle, path = tempfile.mkstemp(suffix=suffix)
    os.close(handle)
    return path


# --------------------------------------------------------------------------
# prompt assembly
# --------------------------------------------------------------------------

def test_prompt_contains_transcript_dots_and_context():
    system, user = ta.build_analysis_prompt(
        TRANSCRIPT, [DOT_A, DOT_B], year="Year 11",
        focus_area="Interactive media and the user experience", lang="en",
    )
    assert "design thinking: empathise, define" in user
    assert "1. " + DOT_A in user and "2. " + DOT_B in user
    assert "Year: Year 11" in user
    assert "Interactive media and the user experience" in user
    assert "English" in user
    # strict output contract lives in the system role
    assert "JSON" in system and "coverage" in system and "covered" in system
    assert "verbatim" in system.lower()
    assert "unsure" in system.lower()


def test_prompt_unset_focus_area_is_marked():
    _, user = ta.build_analysis_prompt(TRANSCRIPT, [DOT_A], year="Year 12", focus_area="")
    assert "(not specified" in user
    assert "Year: Year 12" in user


def test_prompt_language_zh():
    _, user = ta.build_analysis_prompt(TRANSCRIPT, [DOT_A], lang="zh")
    assert "Simplified Chinese" in user


def test_prompt_truncates_long_transcript():
    long_text = "A" * ta.MAX_TRANSCRIPT_CHARS + "TAIL_MARKER_SHOULD_BE_CUT"
    _, user = ta.build_analysis_prompt(long_text, [DOT_A])
    assert "TAIL_MARKER_SHOULD_BE_CUT" not in user
    assert "truncated" in user.lower()
    assert str(ta.MAX_TRANSCRIPT_CHARS) in user


def test_prompt_without_dot_points_is_marked():
    _, user = ta.build_analysis_prompt(TRANSCRIPT, [])
    assert "(no dot points supplied)" in user


# --------------------------------------------------------------------------
# analyze_lesson with a mocked LLM
# --------------------------------------------------------------------------

def test_analyze_lesson_structure_with_mock_llm():
    calls = []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_ANALYSIS)], calls)):
        out = ta.analyze_lesson(TRANSCRIPT, year="Year 11",
                                expected_dot_points=[DOT_A, DOT_B])
    assert set(out) == {"lesson_summary", "strengths", "missed",
                        "coverage", "recommendations"}
    assert len(calls) == 1 and calls[0]["temperature"] == 0.3
    assert TRANSCRIPT[:40] in calls[0]["user"]
    assert "1. " + DOT_A in calls[0]["user"]
    assert len(out["coverage"]) == 2
    assert [c["dot_point"] for c in out["coverage"]] == [DOT_A, DOT_B]
    assert out["coverage"][0]["covered"] is True
    assert "empathise" in out["coverage"][0]["evidence"]
    assert out["coverage"][1]["covered"] is False
    assert out["strengths"] and out["missed"] and out["recommendations"]
    assert len(out["recommendations"]) == 3


def test_analyze_lesson_resolves_dot_points_from_syllabus():
    from agents.lesson_planner import list_modules, load_syllabus, module_dot_points
    syllabus = load_syllabus()
    areas = list_modules(syllabus, "Year 11")
    first_dot = module_dot_points(syllabus, "Year 11", areas[0])[0]["text"]
    year_total = sum(len(module_dot_points(syllabus, "Year 11", a)) for a in areas)
    area_total = len(module_dot_points(syllabus, "Year 11", areas[1]))

    calls = []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_ANALYSIS)], calls)):
        all_year = ta.analyze_lesson(TRANSCRIPT, year="Year 11")
        one_area = ta.analyze_lesson(TRANSCRIPT, year="Year 11",
                                     focus_area=areas[1])
    assert len(all_year["coverage"]) == year_total
    assert first_dot in calls[0]["user"]
    assert len(one_area["coverage"]) == area_total
    assert len(one_area["coverage"]) < len(all_year["coverage"])


def test_coverage_aligns_fills_gaps_and_drops_invented_points():
    calls = []
    messy = {
        "lesson_summary": "One lesson.",
        "strengths": [], "missed": [],
        "coverage": [
            {"dot_point": DOT_A.upper(), "covered": "yes", "evidence": "q1"},
            {"dot_point": "A dot point the teacher never asked about",
             "covered": True, "evidence": "not requested"},
        ],
        "recommendations": ["r1", "r2", "r3"],
    }
    with patched(complete=fake_complete_factory([json.dumps(messy)], calls)):
        out = ta.analyze_lesson(TRANSCRIPT,
                                expected_dot_points=[DOT_B, DOT_A, DOT_C])
    cov = out["coverage"]
    assert [c["dot_point"] for c in cov] == [DOT_B, DOT_A, DOT_C]  # request order kept
    by_dot = {c["dot_point"]: c for c in cov}
    assert by_dot[DOT_A]["covered"] is True          # case-insensitive match, "yes" -> True
    assert by_dot[DOT_A]["evidence"] == "q1"
    assert by_dot[DOT_B]["covered"] is False         # never judged -> not covered
    assert by_dot[DOT_B]["evidence"] == "(not judged by the model)"
    assert len(cov) == 3                             # invented entry dropped


def test_coverage_matches_containment_variants():
    calls = []
    messy = {
        "lesson_summary": "s", "strengths": [], "missed": [],
        "coverage": [{"dot_point": "the user experience (UX)",
                      "covered": True, "evidence": "q"}],
        "recommendations": [],
    }
    with patched(complete=fake_complete_factory([json.dumps(messy)], calls)):
        out = ta.analyze_lesson(TRANSCRIPT, expected_dot_points=[DOT_B])
    assert out["coverage"][0]["covered"] is True


def test_covered_value_coercion_defaults_to_false():
    calls = []
    data = {
        "lesson_summary": "s", "strengths": [], "missed": [],
        "coverage": [
            {"dot_point": DOT_A, "covered": "yes", "evidence": ""},
            {"dot_point": DOT_B, "covered": "no", "evidence": ""},
            {"dot_point": DOT_C, "covered": None, "evidence": ""},
        ],
        "recommendations": [],
    }
    with patched(complete=fake_complete_factory([json.dumps(data)], calls)):
        out = ta.analyze_lesson(TRANSCRIPT,
                                expected_dot_points=[DOT_A, DOT_B, DOT_C])
    assert [c["covered"] for c in out["coverage"]] == [True, False, False]


def test_messy_output_is_normalised():
    calls = []
    messy = {
        "lesson_summary": "   ",
        "strengths": "not a list",
        "missed": ["a", "a", "", 5],
        "coverage": [{"dot_point": DOT_A, "covered": 1, "evidence": " quote "}],
        "recommendations": ["r1", "r2", "r3", "r4", "r5", "r6", "r7", "r1"],
    }
    with patched(complete=fake_complete_factory([json.dumps(messy)], calls)):
        out = ta.analyze_lesson(TRANSCRIPT, expected_dot_points=[DOT_A])
    assert out["lesson_summary"] == "(no lesson summary returned)"
    assert out["strengths"] == []
    assert out["missed"] == ["a", "5"]
    assert out["coverage"][0]["covered"] is True     # 1 -> True
    assert out["coverage"][0]["evidence"] == "quote"
    assert out["recommendations"] == ["r1", "r2", "r3", "r4", "r5"]   # capped at 5


def test_analyze_lesson_retries_once_on_invalid_json():
    calls = []
    replies = ["I cannot help with that.", json.dumps(FAKE_ANALYSIS)]
    with patched(complete=fake_complete_factory(replies, calls)):
        out = ta.analyze_lesson(TRANSCRIPT, expected_dot_points=[DOT_A, DOT_B])
    assert len(calls) == 2
    assert "IMPORTANT" in calls[1]["user"]
    assert out["coverage"][0]["covered"] is True


def test_analyze_lesson_retries_when_coverage_missing():
    calls = []
    replies = [json.dumps({"lesson_summary": "no coverage here"}),
               json.dumps(FAKE_ANALYSIS)]
    with patched(complete=fake_complete_factory(replies, calls)):
        out = ta.analyze_lesson(TRANSCRIPT, expected_dot_points=[DOT_A, DOT_B])
    assert len(calls) == 2
    assert len(out["coverage"]) == 2


def test_analyze_lesson_raises_after_two_failures():
    calls = []
    with patched(complete=fake_complete_factory(["not json at all"], calls)):
        try:
            ta.analyze_lesson(TRANSCRIPT, expected_dot_points=[DOT_A])
        except RuntimeError as exc:
            assert "failed" in str(exc)
        else:
            raise AssertionError("expected RuntimeError after two bad replies")
    assert len(calls) == 2


def test_analyze_lesson_empty_transcript_raises_before_llm():
    calls = []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_ANALYSIS)], calls)):
        for bad in ("", "   ", None):
            try:
                ta.analyze_lesson(bad, expected_dot_points=[DOT_A])  # type: ignore[arg-type]
            except ValueError:
                pass
            else:
                raise AssertionError(f"expected ValueError for {bad!r}")
    assert calls == []


def test_analyze_lesson_without_resolvable_dot_points_raises():
    calls = []
    with patched(complete=fake_complete_factory([json.dumps(FAKE_ANALYSIS)], calls),
                 default_dot_points=lambda year, area="": []):
        try:
            ta.analyze_lesson(TRANSCRIPT, year="Year 99")
        except ValueError as exc:
            assert "dot points" in str(exc)
        else:
            raise AssertionError("expected ValueError when no dot points resolve")
    assert calls == []


# --------------------------------------------------------------------------
# transcribe_audio (fake whisper model; no real model runs)
# --------------------------------------------------------------------------

def test_transcribe_audio_missing_file_is_friendly():
    for bad in ("/no/such/recording.m4a", "", "   ", None):
        try:
            ta.transcribe_audio(bad)  # type: ignore[arg-type]
        except FileNotFoundError as exc:
            assert "audio file not found" in str(exc)
        else:
            raise AssertionError(f"expected FileNotFoundError for {bad!r}")


def test_transcribe_audio_missing_dependency_is_friendly():
    path = temp_audio_file()
    try:
        with blocked_whisper():
            try:
                ta.transcribe_audio(path)
            except RuntimeError as exc:
                assert "faster-whisper is not installed" in str(exc)
                assert "pip install faster-whisper" in str(exc)
            else:
                raise AssertionError("expected RuntimeError when faster-whisper is absent")
    finally:
        os.unlink(path)


def test_transcribe_audio_contract_with_fake_model():
    model_cls, calls = fake_model_factory(
        [SimpleNamespace(text=" Welcome everyone."),
         SimpleNamespace(text=" Today we start with design thinking.")],
        SimpleNamespace(language="en", duration=1842.64),
    )
    path = temp_audio_file(".mp3")
    try:
        with fake_whisper(model_cls):
            out = ta.transcribe_audio(path)
    finally:
        os.unlink(path)
    assert set(out) == {"transcript", "segments", "language", "duration_s"}
    assert out["transcript"] == ("Welcome everyone.\n"
                                 "Today we start with design thinking.")
    assert out["segments"] == 2
    assert out["language"] == "en"
    assert out["duration_s"] == 1842.6
    # model requested with the project settings, transcription with VAD
    assert calls[0] == {"size": "small", "device": "cpu", "compute_type": "int8"}
    assert calls[1]["path"] == path
    assert calls[1]["kwargs"].get("vad_filter") is True


def test_transcribe_audio_decoder_failure_is_wrapped():
    model_cls, _ = fake_model_factory([], SimpleNamespace(language="", duration=0), fail=True)
    path = temp_audio_file(".wav")
    try:
        with fake_whisper(model_cls):
            try:
                ta.transcribe_audio(path)
            except RuntimeError as exc:
                assert "transcription failed" in str(exc)
            else:
                raise AssertionError("expected RuntimeError on decoder failure")
    finally:
        os.unlink(path)


def test_default_dot_points_reads_real_syllabus():
    dots = ta.default_dot_points("Year 11")
    assert len(dots) > 20
    assert ta.default_dot_points("Year 99") == []
    assert len(ta.default_dot_points("Year 11", "Principles of cybersecurity")) > 0


# --------------------------------------------------------------------------
# runner (python3 tests/test_transcript_analyzer.py)
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
