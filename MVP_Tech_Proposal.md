# MVP Technical Proposal — AI Real-Time Coach for HSC Qualitative Subjects

**Team iSoft AI Innovation | v0.1 | Prepared by: Xing (new member)** | Date: 26 Aug 2026

---

## 1. What this is

A proposal for the **smallest working version** of our chosen idea: an AI coach that
marks HSC short-answer responses against official NESA marking guidelines, returns a
**mark + confidence + personalised feedback**, and lets teachers verify the AI's work.

Goal: a **demo-ready MVP in ~2 weeks** that proves the concept, gives us a live demo for
the pitch, and gives us real user-feedback quotes to talk about.

---

## 2. MVP Scope — what we build (and what we deliberately DON'T)

### ✅ IN (Pipeline 1 only, one subject)
| Item | Detail |
|---|---|
| Subject | ONE HSC qualitative subject (candidate: **Enterprise Computing** — public past papers + official marking guidelines exist) |
| Questions | 5-10 real past-paper short-answer questions + official NESA marking guidelines |
| Student flow | Type/paste an answer → get: **mark / max**, **confidence level**, **specific feedback**, **1-2 practice questions** targeting their weakest rubric band |
| Teacher flow | See flagged answers → accept / edit / reject the AI mark (one click) |
| Device | Mobile-friendly web page (works in a phone browser — satisfies "runs on phone" for the demo without building a native app) |

### ❌ OUT (later phases — explicitly out of scope for v1)
- Report generation (pipeline 2), lesson-plan generation (pipeline 3), transcript feedback (pipeline 4)
- Fine-tuning, vision capability, native iOS/Android apps, multi-subject support
- Real classroom deployment — we demo, we don't ship

---

## 3. Tech Choices

### 3.1 Model strategy — two tracks (the key decision)

| Track | What | Why | Cost |
|---|---|---|---|
| **A — Hosted open-weight API (NOW)** | Qwen3 / DeepSeek / Llama family served via any OpenAI-compatible API | Demo-quality marking **today**, zero GPU, zero setup. The fastest way to validate that rubric-conditioned marking actually works | < $5 for the whole demo |
| **B — Local small model (NEXT)** | Small open-weight model (e.g. Qwen3-4B / Gemma 4 small / Llama 3.2 3B, GGUF Q4 quantised) via **Ollama** | Proves the "runs on a phone-class device" story the brief demands. Same code, same prompts — only the endpoint URL changes | $0 |

**Why two tracks:** decouple *"does the idea work?"* (Track A, this week) from
*"can we deploy it small?"* (Track B, once marking quality is confirmed). The brief's
open-weight requirement is satisfied either way — both families are open-weight models.

### 3.2 Marking engine — three-pass architecture (the core)

```
Pass 1  GRADER   → rubric-conditioned prompt: question + official NESA marking
                   guidelines + example answers → mark + band-by-band justification
Pass 2  VERIFIER → independent second pass (different model, or same model with
                   different temperature/seed) re-marks the answer
        (this is the "2nd gen AI verifies output" idea from our doc)
Pass 3  FEEDBACK → writes specific, kind, actionable feedback + 1-2 practice
                   questions aimed at the student's weakest band
```

**Confidence interval (simple, honest version):**
- Pass 1 vs Pass 2 mark agree → **high confidence**, auto-accepted
- Marks differ by 1 band → **medium confidence**, teacher sees the disagreement
- Marks differ by 2+ bands → **low confidence**, flagged for teacher review

This is exactly the "teachers only verify flagged/borderline questions" idea from our
signoff — and it's grounded in published research (see §5).

### 3.3 Knowledge base / RAG — the "repository of truth"
- Index NESA marking guidelines + past papers + syllabus glossary into a **vector DB
  (FAISS or Chroma — free, runs locally)**
- Per question, retrieve the relevant rubric fragments and inject them into the prompt
- Fixes the "internet contradicts the course" problem: **we only feed NESA materials**,
  never generic web content

### 3.4 Stack
| Layer | Choice | Why |
|---|---|---|
| Frontend | Single mobile-friendly HTML page (no framework) | Fast, demoable on any phone |
| Backend | **FastAPI** (Python) | Simple; the whole team can read it |
| LLM access | OpenAI-compatible endpoint | One codebase works for Track A (hosted) and Track B (Ollama local) |
| Data | Google Sheets | Matches the "query_data" idea in our doc — rubrics, questions, results |
| Repo | GitHub | Set up this week; no CI needed yet |

---

## 4. Architecture (one diagram)

```
┌─────────────┐   ┌──────────────────┐   ┌─────────────────────────────────┐
│  Phone /     │   │  FastAPI backend │   │  Pass 1 GRADER ──┐               │
│  laptop      │──▶│  (Python)        │──▶│  Pass 2 VERIFIER │──▶ Mark + CI  │
│  browser     │   │                  │   │  Pass 3 FEEDBACK ┘               │
└─────────────┘   └──────────────────┘   └────────┬────────────────────────┘
                                                  │ RAG
                                    ┌─────────────▼──────────────┐
                                    │ NESA docs (marking guides, │
                                    │ past papers, glossary)     │
                                    │ → FAISS/Chroma vector DB   │
                                    └────────────────────────────┘
                       Teacher review page: accept / edit / reject flagged marks
```

---

## 5. Evidence this works (fills our "External research" section)

- **SteLLA — Structured Grading System Using LLMs with RAG** (arXiv:2501.09092):
  RAG + instructor rubric + reference answers significantly improves LLM short-answer
  grading accuracy. This is essentially our design, already validated.
- **Rubric-Conditioned LLM Grading: Alignment, Uncertainty** (arXiv:2601.08843):
  systematic evaluation of LLMs as rubric-based judges, including uncertainty
  estimation — supports our confidence-interval approach.
- **Automatic Short Answer Grading with LLMs** (ACM 2025): open-weight LLMs with rubric
  prompts perform competitively **without** expensive fine-tuning — supports our
  open-weight, no-fine-tuning-yet stance.
- Competitor reference: **marking.ai** (broader marking product; our differentiator stays
  "real-time coaching + confidence + teacher-in-the-loop", not just marking).

---

## 6. Timeline (2.5 weeks → demo)

| Days | Milestone |
|---|---|
| 1-2 | GitHub repo up; pick subject + 5 questions + marking guidelines; single API call marks 1 answer |
| 3-5 | Three-pass engine + confidence logic; test on 10 mock answers (we write them, incl. 2 borderline ones) |
| 6-8 | RAG index of NESA docs; mobile-friendly web UI |
| 9-12 | Teacher review flow; polish; test on a real phone |
| 13+ | User test with 1-2 real students; collect feedback quotes for the pitch ("user feedback" the brief asks for) |

---

## 7. Risks & mitigations

| Risk | Mitigation |
|---|---|
| LLM marks unreliably on a hard question | Verifier disagreement → flag to teacher; borderline cases stay manual by design |
| API cost | Track A ≈ < $5 total; Track B is free and local |
| NESA material copyright / privacy | We only use publicly available HSC materials; no real student data stored |
| No real teacher contact | Demo with mock teacher flow + genuine feedback from student testers |
| Team capacity (known issue) | Every member gets ONE small task (see next section); no single person is a bottleneck |

---

## 8. What we need from the team (decisions for the next meeting)

1. **Confirm subject**: Enterprise Computing vs another HSC qualitative subject (needs past papers + marking guidelines available)
2. **Confirm competition deadline & deliverable format** (Alfos) — so we can lock the timeline
3. **Task split** (suggested):
   - Backend + marking engine: 1-2 people (Python)
   - RAG + NESA data collection: 1 person
   - Frontend UI: 1 person
   - Pitch deck + demo script: 1 person
   - User testing + feedback quotes: everyone (1 hour each)

---

*Proposal v0.1 — open for discussion. Happy to rewrite any section if the team prefers a different direction.*
