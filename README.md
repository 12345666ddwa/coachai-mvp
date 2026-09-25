# CoachAI — AI Real-Time Coach for HSC Enterprise Computing

An AI that marks HSC short answers against the **official NESA marking guidelines**,
with confidence levels and teacher-in-the-loop review — now a **five-application
platform on one engine**: marking, lesson planning, student tracking, student
practice and lesson review.

- **Full progress report:** `CoachAI_Progress_Report_v1.0.docx`
- **Judge walkthrough script:** `docs/demo_script.md`
- **Verification results:** `tests/GOLDEN_REPORT.md`

## The five applications (all delivered, all verified end-to-end)

| Tab | What it does |
|---|---|
| **Marking** | Dual-agent grading (Marker + Verifier) of 2025 HSC questions; privacy-scrubbed pipeline (student data anonymised before any AI call); "suggested mark" tone; feedback quotes the official marking guidelines verbatim; teachers can add their own questions via a form and mark them immediately |
| **Lesson Planner** | Tick real NESA syllabus dot points (all 180 extracted from the official digital syllabus), optionally paste the school's own material, and generate a timed lesson plan with objectives, lesson flow, assessment point and explicit syllabus alignment |
| **Students** | Progress tracker (level, trend with numeric evidence, weak areas, concrete teacher recommendations) + NESA-style personalised report comments that blend in the teacher's own notes with correct pronouns |
| **Practice & Ask** | Targeted practice questions generated from selected syllabus points / weak areas; student Q&A grounded strictly in official NESA material with sources cited (honest "not covered in the course material" path) |
| **Lesson Review** | Upload a lesson recording (faster-whisper transcription) or paste a transcript; per-dot-point coverage check with quoted evidence, strengths, missed items and next-lesson recommendations |

## Status

| Asset | Status |
|---|---|
| Question bank | 18 questions, 2025 HSC Enterprise Computing (first-ever HSC paper for this subject) + official marking guidelines; extensible with teacher-authored questions |
| RAG knowledge base | 4 official NESA Teacher Support Resources indexed (1,046 chunks, Chroma) |
| Marking engine | LangGraph: Marker Agent + Verifier Agent + retrieval + confidence + retry |
| Privacy layer | Deterministic anonymisation (names / emails / phones) before any LLM call; 21 tests |
| Data layer | SQLite store (students, submissions, report comments, notes) with demo seed data |
| Frontend | Gradio app, 5 tabs, EN/CN language switch, phone-friendly |
| Validation | Across three full Golden Set runs: **100% within +/-1 band and zero wild misses, every run**; exact agreement 75-78% (varies only on borderline answers) |
| Test suite | 118 fast tests across 7 suites + live marking regression (`tests/test_mark.py`) |

## Architecture (summary)

NESA materials -> vector store -> [RAG] -> LangGraph state machine:
`load question -> retrieve -> grade (Marker, T=0.5) -> verify (Verifier, T=0.2) -> approve / retry (<=2) / flag for teacher`

Every application is a different exit from the same core (engine + retrieval index +
syllabus dataset + model abstraction layer). All LLM calls go through
`agents/models.py complete()` — swapping providers (DeepSeek now, Gemini free tier /
local Ollama) is one config line.

See `docs/figures/` for architecture diagrams.

## Run it

```bash
pip install -r requirements.txt
# .env: DEEPSEEK_API_KEY=... DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
python3 app.py                # Gradio UI at http://127.0.0.1:7860 (5 tabs)
python3 tests/run_golden.py   # full 32-answer regression (~30-45 min)
python3 tests/test_mark.py    # live marking check: 6/6 gradings + cache (~3 min)
# fast suites (no LLM): test_privacy (21) · test_store (9) · test_custom_questions (10)
#   test_lesson_planner (16) · test_students (20) · test_student_coach (21)
#   test_transcript_analyzer (21)
```

## Data sources (traceable)

- 2025 HSC Enterprise Computing marking guidelines (nsw.gov.au, official)
- 2025 HSC full-mark sample responses (nsw.gov.au, official)
- Question stems: official NESA online exam system (fam.hsconline.nesa.nsw.edu.au)
- Syllabus dot points: NESA official digital syllabus (curriculum.nsw.edu.au)
- 4x NESA Teacher Support Resources (Year 12 modules) — provided by the team
