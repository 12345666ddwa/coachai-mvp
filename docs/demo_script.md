# CoachAI — Demo Script (Live Walkthrough)
**For judges / team rehearsal · Paper-and-red-pen product demo**
Version 1.0 · 25 Sep 2026 · Prepared by Xing (Happy)

---

## The one-line story

> "Marking is the most hated part of teaching. We built an AI that does the first pass — with the teacher still in charge — and turned every marked answer into teaching signals for the whole classroom."

Flow: **Mark → Plan → Track → Coach → Review** (one engine, five applications).

---

## Setup checklist (before the demo)

| Item | Detail |
|---|---|
| App | Local Gradio running from `ai-coach/` (`python3 app.py`), or the tunnel URL |
| Demo data | `data/coachai.db` seeded (3 demo students: Alex, Priya, Sam) |
| Tab 1 (Marking) | Question `ec2025-q14` (memes) selected, sample answer ready to paste |
| Tab 2 (Lesson) | Year 12 / Data science / 3-4 dot points pre-ticked |
| Tab 3 (Students) | Student "Alex Chen" visible in dropdown |
| Tab 4 (Practice) | Question ready: "What is the difference between interval and ratio data?" |
| Tab 5 (Review) | A short lesson transcript saved in a notepad file to paste |
| **Backup** | **Recorded video of the full flow (network insurance)** |
| Language | Switch EN / 中文 once at the start to show both interfaces |

---

## Walkthrough (12-15 min)

### 0. The problem (45 sec, no screen)

- "TALIS 2024: half of Australian teachers say marking load is unmanageable."
- "Students get a mark and don't know why — research on feedback shows they cannot tell what they did well or what to change."
- "Online explanations contradict what the course actually requires. Students burn energy on the wrong version."
- "CoachAI addresses all three: first-pass marking, explainable feedback, and answers grounded only in official NESA material."

### 1. Marking tab — the core (4 min)

**Screen actions:**
1. Show the question selector. Pick the EC 2025 q14 (memes) question.
2. Point at the table in the question (shares / likes / sentiment) — "the AI sees the full question, including the data table."
3. Paste a student answer that **contains a name and an email** — this is deliberate.
4. Click **Mark this answer**.

**Talking points while it runs (30-60 sec):**
- "While it marks, note two things: the answer we pasted had a student name and an email in it. Watch the result — the real name comes back in the displayed feedback, but the AI itself only ever saw `[STUDENT_1]` and `[EMAIL_1]`. That's our privacy layer — student data is anonymised before it leaves the school."
- "Under the hood this is not one model guessing: a Marker agent grades against the official rubric, then a second independent Verifier agent audits the mark and the reasoning. If they disagree, the answer is flagged for the teacher."

**When the result appears:**
- Point at the score: "This is a **suggested mark** — the teacher confirms or adjusts. We deliberately never present the AI as the final authority."
- Point at the confidence scale: "88% confidence. When confidence drops, the answer is automatically flagged for human review. The AI knows what it doesn't know."
- Point at the feedback sections: "Each 'to improve' point quotes the **official marking guideline**, word for word. Not vibes — the actual rubric."
- Close with the number: "We validated against 32 answers marked from the official 2025 guidelines: 78% exact match with the human rubric, 100% within one mark, zero wild misses."

### 2. Lesson Planner tab (2-3 min)

**Screen actions:**
1. Switch to the Lesson Planner tab.
2. Year 12 → Data science → tick 3 dot points (they're real NESA syllabus points).
3. Paste a short reference text (or leave empty and explain the email workflow).
4. Click **Generate lesson plan**.

**Talking points:**
- "The checklist is the actual NESA syllabus — we extracted all 180 dot points from the official digital syllabus. Teachers tick what they want covered."
- "The generated plan has learning objectives, a timed lesson flow, an assessment point, and an explicit syllabus alignment list."
- "If the school emails us their own teaching material, the planner follows their terminology and scope."

### 3. Students tab — tracker + reports (3 min)

**Screen actions:**
1. Select "Alex Chen" in the dropdown.
2. Click **Analyse progress**.
3. Then generate a report comment for "Priya Sharma" with a teacher note typed in: "She should aim to achieve top results in the final exam."

**Talking points:**
- "This is the student tracker: level, trend with the numbers behind it (33% → 67% → 100%), and concrete recommendations for the teacher."
- "And this is report season solved: the comment is personalised, uses the student's name and correct pronouns, and **blends in the teacher's own note** naturally. The teacher stays the author; the AI does the drafting."

### 4. Practice tab — student side (2 min)

**Screen actions:**
1. Tick 2 dot points → generate practice questions.
2. Then type in the Ask box: "What is the difference between interval and ratio data? My friend said they are the same."

**Talking points:**
- "Practice questions are generated against the syllabus points — targeted, not random."
- "The answer cites where it comes from in the official course material. If the material doesn't cover something, it says so instead of inventing. That's our answer to the contradictory-information problem."

### 5. Lesson Review tab — AI sits in the classroom (2 min)

**Screen actions:**
1. Paste the prepared lesson transcript.
2. Click analyse.

**Talking points:**
- "Feed it a recording of a lesson — it transcribes and checks it against the syllabus."
- "It shows exactly which dot points were covered, with quotes as evidence, what was missed, and what to do next lesson. Like a teaching coach that never runs out of patience."

### 6. Close (1 min)

- "One engine, five applications: marking, planning, tracking, coaching, review. All grounded in official NESA material, all with the teacher in control."
- "Next steps: fine-tuning a small open-weight model for fully offline, zero-cost deployment; extending beyond Enterprise Computing to other qualitative subjects."
- Thanks + team credit.

---

## Backup plans

| Risk | Mitigation |
|---|---|
| Network dies / tunnel down | Run local-only (localhost), or play the **recorded video** |
| LLM slow during demo | Pre-warm: mark one answer before the judges arrive; pick the fastest question |
| A feature errors live | Stay calm, say "let me show the recorded run of this step", continue |
| Judges ask "did AI build this?" | "We built every module in this repo — engine, data layer, privacy layer, UI. AI assisted; the architecture and validation are ours." |

## Likely judge questions (prepared answers)

- **Fine-tuning?** "Not needed for v1 — we validated prompt + RAG beating the need for it (see published 2025 research on short-answer grading). Our roadmap fine-tunes a small open model for offline deployment."
- **Privacy?** "Anonymisation happens on the school's side before any AI call. The model never sees names, emails or phone numbers."
- **vs marking.ai?** "They mark. We close the loop: marking feeds planning, tracking, coaching and lesson review — and our feedback quotes the official rubric."
- **Accuracy?** "78% exact, 100% within one band on our 32-answer validation. And the system flags its own low-confidence marks for teachers."
- **Data ownership?** "Report comments are drafts until the teacher saves them; student data stays in the local SQLite until the school chooses otherwise."

---

## File references (for rehearsing)

- App: `python3 app.py` → http://127.0.0.1:7860
- Demo DB: `data/coachai.db` (re-seed: `python3 tests/seed_golden.py`)
- Validation report: `docs/GOLDEN_REPORT.md` (baseline: 78.1% / 100%)
- Full test suite: 118 tests across 7 suites + `tests/test_mark.py` (live LLM)
