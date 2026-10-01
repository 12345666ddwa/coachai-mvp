#!/usr/bin/env python3
"""
CoachAI demo video recorder v2 (Playwright).

Fixes over v1:
  * case-insensitive result detection
  * lesson planner: click 3 SPECIFIC dot points (not blanket check()), verify count
  * practice tab: type the question into the "YOUR QUESTION" box (by placeholder)
  * lesson review: set Year 12 + Data science, verify analysis actually runs
  * longer waits where the LLM is genuinely slow

Modes: DRY=1 (screenshots only, default) / DRY=0 (records video to /tmp/coachai_demo/)
"""
import os
import re
import sys
import time
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7860/"
DEFAULT_TIMEOUT_MS = 5000   # fail fast; Gradio pages can have stale locators
DRY = os.getenv("DRY", "1") == "1"
STEP_DIR = Path("/tmp/demo_steps")
VIDEO_DIR = Path("/tmp/coachai_demo")
STEP_DIR.mkdir(exist_ok=True)
VIDEO_DIR.mkdir(exist_ok=True)

step_no = [0]
marks = []


def snap(page, label):
    step_no[0] += 1
    marks.append((label, time.time()))
    if DRY:
        p = STEP_DIR / f"v2_{step_no[0]:02d}_{label.replace(' ', '_')[:40]}.png"
        page.screenshot(path=str(p))
        print(f"[{step_no[0]:02d}] {label}", flush=True)
    else:
        print(f"[{step_no[0]:02d}] {label}", flush=True)


def wait(page, s):
    time.sleep(s)


def body_lower(page):
    return page.inner_text("body").lower()


def click_visible(page, text, exact=False, timeout=6000):
    """Click the FIRST VISIBLE element with this text (other tabs may hold hidden twins)."""
    loc = page.locator(f'[role="tabpanel"]:visible').last
    el = loc.get_by_text(text, exact=exact).first
    el.click(timeout=timeout)
    return True


def wait_for(page, *keywords, timeout=150, poll=4):
    """Wait until any keyword (case-insensitive) appears in the page text."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        wait(page, poll)
        body = body_lower(page)
        if any(k.lower() in body for k in keywords):
            return True
    return False


def run(page):
    page.goto(URL, timeout=30000, wait_until="load")
    wait(page, 6)
    snap(page, "01_initial")

    # English UI
    radios = page.get_by_role("radio").all()
    if len(radios) >= 2:
        radios[1].click()
        wait(page, 2)
    snap(page, "02_english")

    # ============ TAB 1 : MARKING ============
    page.get_by_role("tab", name="Marking").click()
    wait(page, 2)
    snap(page, "03_marking_tab")

    page.get_by_role("combobox").first.click()
    wait(page, 1.5)
    snap(page, "04_question_dropdown")
    page.get_by_role("option").filter(has_text="memes").first.click()
    wait(page, 2)
    snap(page, "05_question_chosen")

    page.get_by_text("Load example: strong answer", exact=False).first.click()
    wait(page, 2)
    snap(page, "06_sample_loaded")

    page.get_by_role("button", name="Mark my answer").click()
    snap(page, "07_clicked_mark")
    ok = wait_for(page, "SUGGESTED MARK", "strengths", timeout=150)
    wait(page, 3)
    snap(page, "08_result")
    print("   marking result:", ok, flush=True)
    page.mouse.wheel(0, 400)
    wait(page, 2)
    snap(page, "09_result_scrolled")

    # ============ TAB 2 : LESSON PLANNER ============
    page.get_by_role("tab", name="Lesson planner").click()
    wait(page, 2)
    snap(page, "10_lesson_tab")
    click_visible(page, "Year 12")
    wait(page, 2)
    snap(page, "11_year12")

    # module dropdown: pick Data science
    combos = page.get_by_role("combobox").all()
    if combos:
        combos[-1].click()
        wait(page, 1.5)
        try:
            page.get_by_role("option").filter(has_text="Data science").first.click(timeout=4000)
        except Exception:
            page.get_by_text("Data science", exact=True).first.click(timeout=4000)
        wait(page, 2.5)
    snap(page, "12_module_chosen")

    # tick 3 specific dot points by clicking their label text
    wanted = [
        "Explore the difference between quantitative and qualitative data",
        "Determine which data types are used to represent",
        "Investigate data sampling",
    ]
    for w in wanted:
        try:
            page.get_by_text(w, exact=False).first.click(timeout=4000)
            wait(page, 0.8)
        except Exception as e:
            print("   tick failed:", w[:40], e, flush=True)
    wait(page, 1)
    snap(page, "13_three_ticked")
    # verify the counter
    cnt = page.get_by_text(re.compile(r"Selected:\s*\d+")).first.inner_text() if page.get_by_text(re.compile(r"Selected:\s*\d+")).count() else "(no counter)"
    print("   counter:", cnt, flush=True)

    page.get_by_role("button", name="Generate lesson plan").click()
    snap(page, "14_clicked_generate")
    ok = wait_for(page, "Learning objectives", "Lesson flow", timeout=180)
    wait(page, 3)
    snap(page, "15_plan")
    print("   lesson plan:", ok, flush=True)
    page.mouse.wheel(0, 500)
    wait(page, 2)
    snap(page, "16_plan_scrolled")

    # ============ TAB 3 : STUDENTS ============
    page.get_by_role("tab", name="Students").click()
    wait(page, 2)
    snap(page, "17_students_tab")
    page.get_by_role("button", name="Analyse progress").click()
    snap(page, "18_clicked_analyse")
    ok = wait_for(page, "trend", "recommendations", timeout=150)
    wait(page, 2)
    snap(page, "19_profile")
    print("   profile:", ok, flush=True)

    try:
        page.get_by_placeholder(re.compile("period|term", re.I)).first.fill("Term 3 2026", timeout=5000)
    except Exception as e:
        print("   period fill:", str(e)[:80], flush=True)
    try:
        note_box = page.get_by_placeholder(re.compile("Observations", re.I)).first
        note_box.fill("She should aim to achieve top results in the final exam.", timeout=5000)
        wait(page, 1)
    except Exception as e:
        print("   note fill:", str(e)[:80], flush=True)
    snap(page, "20_note_typed")
    try:
        page.get_by_role("button", name="Generate comment").click()
        snap(page, "21_clicked_comment")
        ok = wait_for(page, "save to records", "draft", timeout=180)
        wait(page, 3)
    except Exception as e:
        print("   comment:", str(e)[:80], flush=True)
    snap(page, "22_comment")
    page.mouse.wheel(0, 400)
    wait(page, 2)
    snap(page, "23_comment_scrolled")

    # ============ TAB 4 : PRACTICE & ASK ============
    page.get_by_role("tab", name="Practice").click()
    wait(page, 2)
    snap(page, "24_practice_tab")
    # scope: Year 12 + Data science (same as the planner flow)
    try:
        click_visible(page, "Year 12")
        wait(page, 2)
        panel = page.locator('[role="tabpanel"]:visible').last
        combos = panel.get_by_role("combobox").all()
        if combos:
            combos[-1].click()
            wait(page, 1.5)
            page.get_by_role("option").filter(has_text="Data science").first.click(timeout=5000)
            wait(page, 2.5)
    except Exception as e:
        print("   practice scope:", str(e)[:80], flush=True)
    snap(page, "24b_practice_scope")
    # tick two syllabus points by text on this tab
    for w in ["Explore the difference between quantitative", "Explore nominal, ordinal, interval"]:
        try:
            click_visible(page, w)
            wait(page, 0.8)
        except Exception as e:
            print("   tick:", w[:35], str(e)[:60], flush=True)
    snap(page, "25_points_ticked")
    try:
        page.get_by_role("button", name="Generate practice").click()
        snap(page, "26_clicked_practice")
        ok = wait_for(page, "hint", timeout=180)
        wait(page, 2)
    except Exception as e:
        print("   practice:", str(e)[:80], flush=True)
        ok = False
    snap(page, "27_practice")
    print("   practice set:", ok, flush=True)

    # ask box (placeholder-based)
    try:
        qbox = page.get_by_placeholder(re.compile("Ask about the course material", re.I)).first
        qbox.click()
        qbox.fill("What is the difference between interval and ratio data? My friend said they are the same thing.")
        wait(page, 1)
    except Exception as e:
        print("   ask fill:", str(e)[:100], flush=True)
    snap(page, "28_question_typed")
    try:
        page.get_by_role("button", name="Ask", exact=True).click()
        snap(page, "29_clicked_ask")
        ok = wait_for(page, "sources", timeout=150)
        wait(page, 2)
    except Exception as e:
        print("   ask:", str(e)[:80], flush=True)
        ok = False
    snap(page, "30_answer")
    print("   answer:", ok, flush=True)

    # ============ TAB 5 : LESSON REVIEW ============
    page.get_by_role("tab", name="Lesson review").click()
    wait(page, 2)
    snap(page, "31_review_tab")
    # Year 12 + module Data science
    try:
        click_visible(page, "Year 12")
        wait(page, 2)
        panel = page.locator('[role="tabpanel"]:visible').last
        combos = panel.get_by_role("combobox").all()
        if combos:
            combos[-1].click()
            wait(page, 1.5)
            page.get_by_role("option").filter(has_text="Data science").first.click(timeout=5000)
            wait(page, 2.5)
    except Exception as e:
        print("   scope select:", str(e)[:80], flush=True)
    snap(page, "32_scope_set")

    transcript = (
        "Okay everyone, today we're looking at data quality and the different types of data. "
        "First, quick recap: quantitative data is numbers you can measure, like height in centimetres or temperature. "
        "Qualitative data describes qualities, like hair colour or the sentiment of a review. That's the key difference. "
        "Now, levels of measurement. Nominal is just categories with no order, like colours. Ordinal has an order but "
        "the gaps aren't equal, like a satisfaction survey from one to five. We won't get to interval and ratio today, "
        "but read ahead if you can. Right, let's practice on the worksheet."
    )
    try:
        tas = page.locator("textarea").all()
        target = max(tas, key=lambda t: (t.bounding_box() or {"height": 0})["height"])
        target.fill(transcript)
        wait(page, 1)
    except Exception as e:
        print("   transcript fill:", str(e)[:80], flush=True)
    snap(page, "33_transcript_pasted")

    try:
        page.get_by_role("button", name="Analyse transcript").click()
        snap(page, "34_clicked_analyse")
        ok = wait_for(page, "covered", "coverage", timeout=180)
        wait(page, 3)
    except Exception as e:
        print("   review:", str(e)[:80], flush=True)
        ok = False
    snap(page, "35_coverage")
    print("   coverage:", ok, flush=True)
    page.mouse.wheel(0, 500)
    wait(page, 2)
    snap(page, "36_final")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        if DRY:
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        else:
            ctx = browser.new_context(
                viewport={"width": 1440, "height": 900},
                record_video_dir=str(VIDEO_DIR),
                record_video_size={"width": 1440, "height": 900},
            )
        page = ctx.new_page()
        try:
            run(page)
        finally:
            marks.append(("__end__", time.time()))
            ctx.close()
            browser.close()
            json.dump(marks, open(VIDEO_DIR / "timestamps.json", "w"), indent=1)
            print("done, marks:", len(marks))


if __name__ == "__main__":
    main()
