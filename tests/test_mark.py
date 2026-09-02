#!/usr/bin/env python3
"""
CoachAI Workflow 1 integration test — real questions, real LLM calls.

3 real HSC Enterprise Computing questions × (1 deliberately poor answer + 1
good answer) = 6 genuine gradings through mark_answer(). Asserts the result
contract, prints a summary table, and verifies the in-memory cache path.

Run:  python3 tests/test_mark.py
"""
import json
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from graphs.mark_graph import CACHE_HITS, clear_cache, mark_answer  # noqa: E402

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_mark_run.log")

# ---------------------------------------------------------------- test answers

CASES = [
    # ec2025-q14 (3 marks): memes → advertising effectiveness
    ("ec2025-q14", "poor",
     "Memes are funny pictures on the internet. The company can look at the memes "
     "and if people like them then the ad campaign is working. It is very useful."),
    ("ec2025-q14", "good",
     "Memes can be analysed quantitatively by tracking their frequency of sharing, "
     "reach and spread across platforms, which data mining tools can turn into "
     "engagement metrics revealing how viral the campaign has become. They can also "
     "be analysed qualitatively: examining the themes, tone and sentiment of meme "
     "comments and remixes reveals audience perception of the brand, so the company "
     "can judge whether the campaign is being received positively."),
    # ec2025-q16a (4 marks): hardware + specific sensors for intelligent system
    ("ec2025-q16a", "poor",
     "They need computers and some cameras to check the TV screens. Sensors are "
     "used to sense stuff. It makes the factory better."),
    ("ec2025-q16a", "good",
     "The intelligent system needs sensors to collect live data from the production "
     "line and hardware to transmit it to a server for processing. Cameras capture "
     "visual data of the LCD panels during the brightness test so faulty screens can "
     "be detected automatically. Vibration sensors on the robotic assembly arm detect "
     "abnormal machine wear and can prevent breakdowns, while proximity sensors check "
     "the LCD panel is correctly positioned before the motherboard is attached. "
     "Temperature sensors monitor the environment around the manufacturing equipment. "
     "This sensor data is sent over the network (e.g. via an IoT gateway) to the "
     "server, where the intelligent system analyses it in real time."),
    # ec2025-q20 (3 marks): spreadsheet features → visual understanding for marine biologist
    ("ec2025-q20", "poor",
     "Use Excel to show the numbers. The biologist can make a chart with the data."),
    ("ec2025-q20", "good",
     "Charts and graphs visualise the raw datasets — for example a line chart of "
     "water temperature over time reveals seasonal trends the biologist can use to "
     "predict fish population shifts. Conditional formatting highlights cells where "
     "pollution levels exceed a threshold, drawing attention to anomalies at a "
     "glance. Sparklines inside cells give a compact trend view for every sample "
     "site, and a pivot table can aggregate food availability by season and region "
     "so relationships between the three datasets become visually obvious."),
]


def summary_row(qid: str, kind: str, r: dict, elapsed: float) -> str:
    if r.get("status") == "error":
        return f"{qid:<12} {kind:<6} ERROR   {r.get('error', '')[:90]}"
    return (f"{qid:<12} {kind:<6} {r['status']:<8} marks {r['marks']:>2}/{r['max_marks']:<2} "
            f"conf {r['confidence_pct']:>3}%/{r['confidence_level']:<6} "
            f"attempts {r['attempts']}  ({elapsed:.0f}s)")


def main() -> int:
    clear_cache()
    t0 = time.time()
    rows, failures = [], 0
    log_lines = [f"CoachAI Workflow1 test run @ {time.strftime('%Y-%m-%d %H:%M:%S')}", "=" * 100]

    for qid, kind, answer in CASES:
        start = time.time()
        r = mark_answer(qid, answer)
        elapsed = time.time() - start

        # ---- contract assertions (error dicts are a legitimate pipeline response)
        assert isinstance(r, dict), f"{qid}/{kind}: result not a dict: {r!r}"
        if r.get("status") == "error":
            failures += 1
            row = f"{qid:<12} {kind:<6} ERROR   {str(r.get('error',''))[:90]}"
            rows.append(row)
            log_lines.append(f"{qid}/{kind} ERROR: {r.get('error')}")
            print(row, flush=True)
            continue

        assert r["status"] in ("approved", "flagged"), r["status"]
        for key in ("status", "marks", "confidence_pct"):
            assert key in r, f"{qid}/{kind}: missing key {key!r} in {sorted(r)}"
        assert 0 <= r["marks"] <= r["max_marks"], r
        assert 0 <= r["confidence_pct"] <= 100, r
        assert r["confidence_level"] in ("high", "medium", "low"), r
        assert isinstance(r["feedback"], list), r
        assert isinstance(r["flags"], list), r
        assert isinstance(r["attempts"], int) and 1 <= r["attempts"] <= 3, r

        row = summary_row(qid, kind, r, elapsed)
        rows.append(row)
        log_lines.append(row)
        log_lines.append("  marks=%s | flags=%s | conf=%s" %
                         (r.get("marks"), r.get("flags"), r.get("confidence_pct")))
        log_lines.append("  justification: " + str(r.get("justification", ""))[:400])
        for fb in r.get("feedback", [])[:4]:
            log_lines.append(f"    [{fb.get('type')}] {str(fb.get('text'))[:180]}")
        print(row, flush=True)

    # ---- cache path check: identical request must hit the in-memory cache
    before = CACHE_HITS
    mark_answer(CASES[0][0], CASES[0][2])  # same qid + same answer → must hit cache
    log_lines.append(f"cache: hits before={before} after={CACHE_HITS} (identical request served from cache)")
    assert CACHE_HITS == before + 1, "identical request did not hit the cache"
    print(f"cache OK: repeated request served from memory cache (hits={CACHE_HITS})", flush=True)

    # ---- error path: unknown question id must return error dict, not raise
    r_err = mark_answer("ec2025-q999", "some answer")
    assert r_err["status"] == "error" and "error" in r_err
    log_lines.append(f"error path OK: unknown question -> {r_err['status']}")
    print(f"error path OK: unknown question_id -> status={r_err['status']}", flush=True)

    # ---- empty answer guard
    r_empty = mark_answer("ec2025-q14", "   ")
    assert r_empty["status"] == "error"
    log_lines.append("empty-answer guard OK")

    elapsed_total = time.time() - t0
    log_lines.append("=" * 100)
    log_lines.append(f"TOTAL {len(CASES)} gradings in {elapsed_total:.0f}s | errors={failures}")
    with open(LOG_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(log_lines) + "\n")

    print(f"\nsummary: {len(CASES) - failures}/{len(CASES)} gradings OK in {elapsed_total:.0f}s "
          f"— details in {LOG_PATH}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
