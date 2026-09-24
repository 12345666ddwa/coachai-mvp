#!/usr/bin/env python3
"""
CoachAI — privacy.anonymizer test suite.

Runs both ways:

    python3 tests/test_privacy.py     # plain asserts, prints PASS per test
    python3 -m pytest tests/test_privacy.py

Covers: known-name replacement (full + single name, case-insensitive, word
boundaries, CJK behaviour), email/phone regexes, stable numbering,
restore round-trips (including the [STUDENT_1]/[STUDENT_10] ordering trap),
nested result-dict walking without mutation, and defensive empty/None input.
"""
import copy
import os
import sys
import traceback
from typing import Any, cast

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from privacy import anonymizer  # noqa: E402

anonymize = anonymizer.anonymize
restore = anonymizer.restore
anonymize_result = anonymizer.anonymize_result
restore_result = anonymizer.restore_result


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _sample_result() -> dict:
    """A realistic marking-engine result dict (shape of mark_answer output)."""
    return {
        "question_id": "ec2025-q14",
        "status": "approved",
        "marks": 5,
        "max_marks": 6,
        "confidence_pct": 85,
        "feedback": [
            {"type": "good", "text": "Alex Chen explained data mining clearly."},
            {"type": "improve", "text": "Alex Chen should cite Jordan Lee's study."},
        ],
        "flags": [],
        "justification": "Band matched for Alex Chen; Jordan Lee missed the tone.",
    }


# --------------------------------------------------------------------------
# tests — package surface & acceptance example
# --------------------------------------------------------------------------

def test_package_surface():
    """`from privacy import ...` re-exports the same functions as the module."""
    import privacy
    assert privacy.anonymize is anonymizer.anonymize
    assert privacy.restore is anonymizer.restore
    assert privacy.anonymize_result is anonymizer.anonymize_result
    assert privacy.restore_result is anonymizer.restore_result


def test_acceptance_example():
    """The exact example from the task spec."""
    safe, mapping = anonymize("Alex Chen emailed alex@gmail.com", ["Alex Chen"])
    assert safe == "[STUDENT_1] emailed [EMAIL_1]", safe
    assert mapping == {"[STUDENT_1]": "Alex Chen",
                       "[EMAIL_1]": "alex@gmail.com"}, mapping


# --------------------------------------------------------------------------
# tests — name replacement
# --------------------------------------------------------------------------

def test_full_name_replacement():
    safe, mapping = anonymize("Alex Chen wrote an excellent essay.", ["Alex Chen"])
    assert safe == "[STUDENT_1] wrote an excellent essay.", safe
    assert mapping == {"[STUDENT_1]": "Alex Chen"}, mapping


def test_single_name_case_insensitive():
    """Single names match case-insensitively; mapping stores first-seen form."""
    safe, mapping = anonymize("jordan spoke; JORDAN nodded; JoRdAn left.", ["Jordan"])
    assert safe == "[STUDENT_1] spoke; [STUDENT_1] nodded; [STUDENT_1] left.", safe
    assert mapping == {"[STUDENT_1]": "jordan"}, mapping
    # Case variants collapse onto one placeholder, so restore() returns the
    # first-seen surface form for every occurrence (documented behaviour).
    assert restore(safe, mapping) == "jordan spoke; jordan nodded; jordan left."

    # A supplied first name also matches inside a full name.
    safe2, _ = anonymize("Jordan Lee studies law.", ["Jordan"])
    assert safe2 == "[STUDENT_1] Lee studies law.", safe2


def test_full_name_beats_single_name():
    """A longer supplied name wins the overlap over a shorter one."""
    safe, mapping = anonymize("Alex Chen left; Alex returned.", ["Alex", "Alex Chen"])
    # "Alex Chen" takes STUDENT_1; the lone "Alex" later is a separate key.
    assert safe == "[STUDENT_1] left; [STUDENT_2] returned.", safe
    assert mapping == {"[STUDENT_1]": "Alex Chen", "[STUDENT_2]": "Alex"}, mapping


def test_word_boundary_announcement():
    """'Ann' must not eat 'Announcement', 'Annie' or 'Annabel'."""
    safe, mapping = anonymize("Announcement: Ann, Annie and Annabel attended.", ["Ann"])
    assert safe == "Announcement: [STUDENT_1], Annie and Annabel attended.", safe
    assert mapping == {"[STUDENT_1]": "Ann"}, mapping


def test_chinese_name_replacement_and_restore():
    """CJK names are matched as plain substrings (no \\b — it misbehaves by CJK)."""
    text = "张伟的作业进步很明显，张伟继续努力。"
    safe, mapping = anonymize(text, ["张伟"])
    assert safe == "[STUDENT_1]的作业进步很明显，[STUDENT_1]继续努力。", safe
    assert mapping == {"[STUDENT_1]": "张伟"}, mapping
    assert restore(safe, mapping) == text

    # Direct substring semantics: a CJK name is also replaced when it sits
    # inside a longer run of characters (no word boundaries in Chinese).
    safe2, mapping2 = anonymize("张伟明同学也提交了。", ["张伟"])
    assert safe2 == "[STUDENT_1]明同学也提交了。", safe2
    assert restore(safe2, mapping2) == "张伟明同学也提交了。"


# --------------------------------------------------------------------------
# tests — pattern replacement (email / phone)
# --------------------------------------------------------------------------

def test_email_replacement():
    safe, mapping = anonymize(
        "Email alex.chen+school@gmail.com or admin@edu.nsw.gov.au.")
    assert safe == "Email [EMAIL_1] or [EMAIL_2].", safe
    assert mapping["[EMAIL_1]"] == "alex.chen+school@gmail.com", mapping
    assert mapping["[EMAIL_2]"] == "admin@edu.nsw.gov.au", mapping
    # The sentence period must survive outside the placeholder.
    assert restore(safe, mapping) == "Email alex.chen+school@gmail.com or admin@edu.nsw.gov.au."


def test_email_containing_name():
    """An email that contains a known name must be anonymized whole, as email."""
    safe, mapping = anonymize("Mail smith@example.com please.", ["Smith"])
    assert safe == "Mail [EMAIL_1] please.", safe
    assert mapping == {"[EMAIL_1]": "smith@example.com"}, mapping


def test_phone_replacement_au_formats():
    text = "Mobile 0412 345 678, intl +61 412 345 678, home (02) 9876 5432."
    safe, mapping = anonymize(text)
    assert safe == "Mobile [PHONE_1], intl [PHONE_2], home [PHONE_3].", safe
    assert mapping == {
        "[PHONE_1]": "0412 345 678",
        "[PHONE_2]": "+61 412 345 678",
        "[PHONE_3]": "(02) 9876 5432",
    }, mapping
    assert restore(safe, mapping) == text


# --------------------------------------------------------------------------
# tests — numbering consistency
# --------------------------------------------------------------------------

def test_repeated_values_share_number():
    """Same value -> same placeholder; different people -> different numbers."""
    text = ("Alex Chen met Jordan Lee. Alex Chen waved at Jordan Lee. "
            "Alex Chen left.")
    safe, mapping = anonymize(text, ["Alex Chen", "Jordan Lee"])
    assert safe == ("[STUDENT_1] met [STUDENT_2]. [STUDENT_1] waved at "
                    "[STUDENT_2]. [STUDENT_1] left."), safe
    assert mapping == {"[STUDENT_1]": "Alex Chen", "[STUDENT_2]": "Jordan Lee"}, mapping

    safe2, mapping2 = anonymize("Ping a@b.com; ping a@b.com again.")
    assert safe2 == "Ping [EMAIL_1]; ping [EMAIL_1] again.", safe2
    assert len(mapping2) == 1


def test_numbering_follows_first_appearance():
    """Numbers are assigned in order of first appearance in the text."""
    text = "Jordan Lee arrived before Alex Chen; Alex Chen disagreed with Jordan Lee."
    safe, mapping = anonymize(text, ["Alex Chen", "Jordan Lee"])
    assert safe == ("[STUDENT_1] arrived before [STUDENT_2]; "
                    "[STUDENT_2] disagreed with [STUDENT_1]."), safe
    assert mapping == {"[STUDENT_1]": "Jordan Lee", "[STUDENT_2]": "Alex Chen"}, mapping


def test_category_numbering_is_independent():
    """Each category counts from 1 on its own."""
    safe, mapping = anonymize("a@b.com Alex Chen 0412 345 678", ["Alex Chen"])
    assert safe == "[EMAIL_1] [STUDENT_1] [PHONE_1]", safe
    assert len(mapping) == 3


# --------------------------------------------------------------------------
# tests — restore
# --------------------------------------------------------------------------

def test_restore_roundtrip_mixed_text():
    text = ("Alex Chen (alex.chen@example.com, 0412 345 678) attends "
            "Macquarie Fields High School. Reach Jordan Lee on (02) 9876 5432.")
    names = ["Alex Chen", "Jordan Lee"]
    schools = ["Macquarie Fields High School"]

    safe, mapping = anonymize(text, names, schools)
    assert safe == ("[STUDENT_1] ([EMAIL_1], [PHONE_1]) attends [SCHOOL_1]. "
                    "Reach [STUDENT_2] on [PHONE_2]."), safe
    for pii in ("Alex Chen", "alex.chen@example.com", "0412 345 678",
                "Macquarie Fields High School", "Jordan Lee", "(02) 9876 5432"):
        assert pii not in safe, pii
    assert restore(safe, mapping) == text


def test_restore_placeholder_prefix_trap():
    """[STUDENT_10] must restore correctly even when [STUDENT_1] also exists."""
    mapping = {"[STUDENT_1]": "Alpha One", "[STUDENT_10]": "Kilo Ten"}
    assert restore("[STUDENT_10] then [STUDENT_1]", mapping) == "Kilo Ten then Alpha One"

    # Generated end-to-end: 10 distinct students -> 1..10, full round-trip.
    names = [f"Person {i}" for i in range(1, 11)]
    text = " ".join(names)
    safe, mapping2 = anonymize(text, names)
    assert safe == " ".join(f"[STUDENT_{i}]" for i in range(1, 11)), safe
    assert "[STUDENT_10]" in safe
    assert restore(safe, mapping2) == text


def test_restore_defenses():
    assert restore("hello world", {}) == "hello world"
    # cast: we deliberately pass a non-dict to exercise the runtime guard.
    assert restore("hello world", cast(Any, None)) == "hello world"
    assert restore("", {"[STUDENT_1]": "A"}) == ""
    # Unknown placeholders stay as-is.
    assert restore("[UNKNOWN_1] stays", {"[STUDENT_1]": "A"}) == "[UNKNOWN_1] stays"


# --------------------------------------------------------------------------
# tests — defensive / optional inputs
# --------------------------------------------------------------------------

def test_empty_and_none_defenses():
    assert anonymize("", ["Alex"]) == ("", {})
    assert anonymize(cast(Any, None), ["Alex"]) == (None, {})
    assert anonymize("No PII here.") == ("No PII here.", {})
    assert anonymize("No PII here.", [], []) == ("No PII here.", {})
    # A bare string instead of a list is treated as one name.
    safe, mapping = anonymize("Alex Chen", "Alex Chen")
    assert safe == "[STUDENT_1]", safe
    assert mapping == {"[STUDENT_1]": "Alex Chen"}, mapping


def test_school_names_optional():
    text = "Report for Macquarie Fields High School."
    # No school list supplied -> school text is untouched.
    safe, mapping = anonymize(text, ["Alex Chen"])
    assert safe == text, safe
    assert mapping == {}
    # With the school list supplied -> replaced with [SCHOOL_n].
    safe2, mapping2 = anonymize(text, ["Alex Chen"], ["Macquarie Fields High School"])
    assert safe2 == "Report for [SCHOOL_1].", safe2
    assert mapping2 == {"[SCHOOL_1]": "Macquarie Fields High School"}, mapping2


# --------------------------------------------------------------------------
# tests — result dicts (grading pipeline integration)
# --------------------------------------------------------------------------

def test_anonymize_result_nested_consistent_no_mutation():
    result = _sample_result()
    before = copy.deepcopy(result)

    safe, mapping = anonymize_result(result, ["Alex Chen", "Jordan Lee"])

    # input untouched; new containers all the way down
    assert result == before
    assert safe is not result
    assert safe["feedback"] is not result["feedback"]
    assert safe["feedback"][0] is not result["feedback"][0]
    assert safe["flags"] is not result["flags"]

    # non-PII values survive untouched
    assert safe["marks"] == 5 and safe["max_marks"] == 6
    assert safe["question_id"] == "ec2025-q14"
    assert safe["feedback"][0]["type"] == "good"

    # strings inside lists of dicts are anonymized with shared numbering
    assert safe["feedback"][0]["text"] == "[STUDENT_1] explained data mining clearly."
    assert safe["feedback"][1]["text"] == "[STUDENT_1] should cite [STUDENT_2]'s study."
    assert safe["justification"] == ("Band matched for [STUDENT_1]; "
                                     "[STUDENT_2] missed the tone.")
    assert mapping == {"[STUDENT_1]": "Alex Chen", "[STUDENT_2]": "Jordan Lee"}, mapping


def test_restore_result_roundtrip():
    result = _sample_result()
    safe, mapping = anonymize_result(result, ["Alex Chen", "Jordan Lee"])
    assert restore_result(safe, mapping) == result
    # Empty mapping: still a new, structurally-equal object (no mutation).
    copy2 = restore_result(result, {})
    assert copy2 == result and copy2 is not result
    assert copy2["feedback"] is not result["feedback"]


def test_anonymize_result_empty_inputs():
    assert anonymize_result({}) == ({}, {})
    res, mapping = anonymize_result({"marks": 5, "flags": []})
    assert res == {"marks": 5, "flags": []} and mapping == {}
    assert res is not None


# --------------------------------------------------------------------------
# runner (python3 tests/test_privacy.py)
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
