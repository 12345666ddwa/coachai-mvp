# CoachAI Master Work Plan v1.0
**Master Work Plan — for Xing (Happy) + Hermes execution**
Last updated: 2026-09-16 | Basis: Direction Confirmation Document (Scope C confirmed) + Alfos's two 9/16 supplements + Kla's feedback + three points from the phone call + design Avoid checklist

---

## 0. One-Line Overview

**Goal**: Upgrade CoachAI from "a completed marking MVP" into a complete product demo covering the **teacher side + student side + teaching-research side** (Scope C + Alfos's supplementary features delivered in layers).
**Working method**: design before code, confirm before kick-off, parallel multi-agent development; the supervisor (Hermes main agent) handles planning, review, acceptance, and reporting only.

---

## 1. Current State Inventory (starting assets, all verified)

| Asset | Status | Evidence |
|---|---|---|
| Marking engine (Marker + Verifier dual agent) | ✅ Running | 18 real 2025 HSC exam questions, confidence scores, teacher review flags |
| Golden Set verification | ✅ | Three full runs (32 submissions each): every run 100% within ±1 band, 0 wild misses; exact 75-78% |
| Question bank (HSC exam questions + official marking guidelines) | ✅ | data/questions.json, 18 questions for a total of 65 marks |
| RAG knowledge base | ✅ | 4 NESA TSR documents, 1046 chunks |
| Model abstraction layer | ✅ | agents/models.py, swap the model with one line of config |
| Gradio UI | ✅ | emoji removed, squared-off styling, full question display |
| Concept site + report + deployment | ✅ | GitHub Pages + Cloudflare Tunnel |
| Transcription pipeline | ✅ | faster-whisper tested (34-minute meeting transcribed) |

---

## 2. Master Requirements List (all sources consolidated; every item has acceptance criteria)

### Table A: Confirmed Scope (Scope C)
| # | Requirement | Source | Priority | Acceptance criteria |
|---|---|---|---|---|
| A1 | UI redesign (anti-AI-coded) | Direction document + avoid checklist | P0 | Pass the avoid checklist item by item; full-width with no dead space; no emoji |
| A2 | Privacy anonymisation layer | Team requirement (proprietary data) | P0 | Name → placeholder → marking → restore; demonstrable side-by-side comparison |
| A3 | Lesson planner (checkbox + import) | Phone call #2 | P0 | Check syllabus dot points → import text → generate a structured lesson plan |
| A4 | Marking upgrade (suggested mark + rubric citation) | Team task list | P0 | Output wording is advisory; every judgement cites a marking guideline line |
| A5 | Custom question creation | Alfos 9/16 #3 | P0 | Teacher enters question / marks / marking guidelines / reference answer → stored → markable |
| A6 | Report generation | Scope C 3.5 | P1 | Marks table + teacher custom comments + gender → NESA-style personalised comments |
| A7 | Full-width web pages | Alfos 9/16 | P0 | Width fully utilised, no dead space on either side |

### Table B: Alfos Supplementary Features (layered delivery)
| # | Requirement | Layer | Acceptance criteria |
|---|---|---|---|
| B1 | Student tracker (progress + teacher recommendations) | L2 | Per student: current level / trend / weak points + recommendations |
| B2 | Student side (question generation + Q&A + mind map) | L3 (question generation + Q&A first) | Targeted question generation; conversational Q&A; mind map (deferred) |
| B3 | Classroom recording analysis (transcript → teaching-research feedback) | L3 | Transcript + check against syllabus dot points for coverage / gaps / highlights |

### Table C: Administrative Tasks
| # | Task | Owner |
|---|---|---|
| C1 | Project rename (candidate name list) | Hermes draft → Xing finalises → team selects |
| C2 | Grant teammates GitHub admin/editor access | Xing (needs usernames) |
| C3 | iLearn competition page research | Xing + Hermes (CDP scraping) |
| C4 | Check for Alfos's marking criteria email (Outlook) | Xing |
| C5 | Lesson topic list (syllabus dot points/outcomes extraction) | Hermes (research + extraction) → team review |
| C6 | Reply to Alfos's call for suggestions (professional report-generation advice) | Hermes draft → Xing sends |

---

## 3. Architecture Blueprint

```
              【 One engine · One knowledge base 】
   ┌────────────────────────────────────────────────────┐
   │  Marking engine + TSR RAG + Question bank +        │
   │  model abstraction layer                           │
   └────────────────────────────────────────────────────┘
        │        │         │         │         │          │
     Marking   Lesson    Report   Tracking  Student   Transcript
    (existing) planner    (new)    (new)     side     analysis
                (new)                       (new)      (new)
        └────── Shared: SQLite data layer + unified UI system ──────┘
```

**New modules (corresponding files)**:
- `store/` — SQLite data layer (marking records / students / marks / custom comments)
- `privacy/anonymizer.py` — anonymisation pipeline
- `agents/lesson_planner.py` — lesson plan generation
- `agents/report_writer.py` — report comment generation
- `agents/tracker.py` — student tracking analysis
- `agents/student_coach.py` — student side (question generation / Q&A)
- `tools/transcript_analyzer.py` — classroom recording analysis
- `data/syllabus.json` — Enterprise Computing syllabus dot points/outcomes (data source for the lesson checklist)

---

## 4. Phase Execution Roadmap (7 phases)

### Phase 0: Preparation ✅ Complete (9/25)
- [x] C1 Project rename: draft 8-10 candidate names (English-primary; education / marking / coaching semantics; avoiding AI-coded tropes)
- [x] C5 Syllabus extraction: NSW Enterprise Computing syllabus dot points + outcomes → first draft of the lesson checkbox list
- [ ] C3 iLearn page scraping (needs Xing to log in)
- [ ] C4 Email check reminder
- **Acceptance**: candidate name list + syllabus checklist + key iLearn information (competition timeline / judging requirements)

### Phase 1: Data Layer ✅ Complete (9/25, commit 5193bde)
- [x] SQLite schema: students / submissions / marks / report_comments / custom_notes
- [x] Storage API + integration with the existing marking pipeline (every marking run auto-persisted)
- [x] Migration script (Golden Set data usable as demo seed)
- **Acceptance**: run one marking → full record visible in the database; historical reruns queryable

### Phase 2: UI Redesign + Privacy Layer 🟡 Mostly Complete (9/25)
> ✅ Design draft v2 (docs/design/, bilingual + real toggle)｜✅ Privacy layer (privacy/, 21 tests + E2E verification)｜⏳ UI implementation pending design sign-off
- [x] Design drafts: marking page + lesson page (HTML mockups, for Xing/team review first)
- [x] Visual implementation: marking-red paper design system (paper #FAFAF7 / ink / marking-red accent / full-width)
- [x] Avoid checklist item-by-item review (logged in table form)
- [x] Anonymisation pipeline: name / school → placeholder → restore; UI comparison demo
- **Acceptance**: confirmed design draft + interactive new UI + anonymisation demo working

### Phase 3: Marking Upgrade + Custom Questions ✅ Complete (9/25, commits e1e110a/49c16b7)
> ✅ Privacy integrated into the app pipeline｜✅ suggested mark tone (marker/verifier prompt)｜✅ rubric citation + anti-fabrication check｜✅ Custom questions (form + questions_io + engine integration, E2E 4/4 verified)
- [x] Output tone overhaul (suggested mark / draft evaluation)
- [x] Rubric line-by-line citation (result card shows "Basis: marking guidelines line X")
- [x] Custom question UI (entry form → questions.json → immediately markable)
- **Acceptance**: new question entry → marking → rubric citation display, full chain

### Phase 4: Lesson Planner ✅ Complete (9/25, commit 9c9781c)
- [ ] Checkbox UI (syllabus dot points checklist)
- [ ] Document import (paste text / file upload)
- [ ] Generation engine (LLM + TSR RAG) → structured lesson plan (objectives / activities / assessment / duration)
- **Dependencies**: Alfos's reference documents (email); if not received, build from NESA TSR materials first
- **Acceptance**: complete flow demo + output quality samples

### Phase 5: Report Generation + Student Tracker ✅ Complete (9/25, commit fa48b65)
- [ ] Report generation: marks table input + teacher custom comments + gender pronouns → NESA-style comments
- [ ] Student tracking: progress profile (level / trend / weak points) + teacher recommendations
- **Dependencies**: Alfos's real marks samples; marking criteria email
- **Acceptance**: runs on real data + benchmarked against nswschoolreports guideline principles

### Phase 6: Student Side + Classroom Recordings ✅ Complete (9/25, commits 484d483/fbc4056)
- [ ] Student side: targeted question generation + conversational Q&A (reusing the engine)
- [ ] Classroom recording analysis: transcription (faster-whisper ready-made) → syllabus coverage check → teaching-research feedback
- [ ] (Deferred) mind map rendering
- **Acceptance**: two demonstrable prototypes (1 complete case each)

### Phase 7: Integration QA + Demo Rehearsal 🟡 Main Body Complete (9/25, commit 7879609)
> ✅ Demo script｜✅ Report updated (honest numbers from three runs)｜✅ 5-Tab launch verification｜✅ Golden Set three full runs (±1 100%/0 miss constant)｜✅ test_mark fixes｜⏳ Tunnel deployment + team trial
- [ ] Full-feature integration + regression testing (Golden Set accuracy not degraded)
- [ ] Team trial round + feedback fixes
- [ ] Demo script design (judge journey: marking → follow-up → lesson plan → report → tracking → recording)
- [ ] Deployment update + report/documentation update
- **Acceptance**: full demo rehearsal passed + deployment online

---

## 5. Roles & Responsibilities (Iron Rules)

| Role | Responsibilities | Prohibited |
|---|---|---|
| **Hermes main pipeline** (main agent) | Planning, solution design, sub-agent delegation, review & acceptance, reporting to Xing, drafting user communications | ❌ Does not personally write large module code (>50 lines goes to a sub-agent) |
| **Sub-agents** (delegate_task) | Module development (≤3 concurrent per batch), testing, fixes | ❌ Do not touch unassigned modules; output must be written to files |
| **Xing (user)** | Requirement confirmation, team communication (messages / documents), data collection (emails / samples), demo acceptance | ❌ No blind technical decisions (everything goes through Hermes analysis) |
| **Teammates (Alfos/Kla et al.)** | Provide sample data, confirm feedback, iLearn information, prioritisation | — |

---

## 6. Multi-Agent Collaboration Plan

### 6.1 Delegation Principles (mandatory)
1. **Large projects must use parallel sub-agents**; the supervisor only plans, reviews, accepts, and reports
2. Multi-agent execution plans are **presented to Xing for confirmation first** before work begins
3. For sub-agent timeouts / errors, **check the scene first** (file mtime + live transcript) before judging; speculation is forbidden
4. When fixes are needed, **dispatch a dedicated fix agent** (with the crash scene); the supervisor does not modify code personally
5. Sub-agent output is **saved to files for review**; report at every Phase

### 6.2 Agent Batch Design

| Batch | Agents (≤3 concurrent) | Dependencies |
|---|---|---|
| Batch 1 | Agent-Data (SQLite layer) + Agent-Design (UI mockups, 2 pages) + Agent-Research (syllabus extraction) | Phase 0/1 parallel |
| Batch 2 | Agent-Privacy (anonymisation) + Agent-Marking (marking upgrade + custom questions) | Depends on Batch 1 design draft |
| Batch 3 | Agent-Lesson (lesson planner) + Agent-Report (report generation) | Depends on data layer |
| Batch 4 | Agent-Tracker (student tracker) + Agent-Student (student side) | Depends on data layer + report architecture |
| Batch 5 | Agent-Transcript (recording analysis) + Agent-QA (full regression verification) | Depends on transcription pipeline |

### 6.3 Per-Batch Delivery Standards
- Deliverables: **code files + test scripts + run evidence (real output)**
- Directory convention: self-contained modules (code / tests / sample data)
- Acceptance: the main pipeline independently reruns verification; **self-reports are not trusted**

---

## 7. Quality & Verification Discipline

1. **Data iron rule**: all numbers must come from real runs; fabrication is forbidden (violation = rework)
2. **Ground Truth verification**: independently recompute at every feature acceptance (e.g. reports: marks table → comments → data points checked)
3. **Design acceptance**: avoid checklist ticked item by item (17 items)
4. **Regression floor**: Golden Set 32 submissions — 100% within ±1 band and 0 wild misses are hard floors (constant across three full runs); exact reference range 75-78%
5. **Demo data anonymisation**: all display data passes through the anonymisation pipeline
6. **Commit discipline**: push once per Phase completion, with a Chinese description

---

## 8. Communication & Delivery Cadence

| Audience | Frequency | Format |
|---|---|---|
| Xing | At each Phase completion + key decision points | Chinese updates + screenshots / files |
| Team (Alfos et al.) | Milestones (every 1-2 Phases) | English documents / group messages + demo links |
| Shared documents | On key updates | Append-only edits (original text preserved) |

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Competition timeline compressed | Features not finished | Layer L1→L2→L3; each layer has a demonstrable version |
| Sample data not received (marks / marking criteria) | Report / tracking features in limbo | Use Golden Set seed data first; prepare both tracks |
| Reference documents not received (lesson planner) | Lesson planner demo lacks real materials | Build from NESA TSR first; swap in once documents arrive |
| Recording-analysis demo data hard to prepare | L3 demo not convincing | Use an existing meeting transcript for the first demo; source classroom recording samples |
| Team feedback changes | Rework | All changes go through the documentation confirmation process |
| Name / IP issues | Rename cascade (docs / repo / demo) | Rename list → team decides; replace uniformly once decided |

---

## 10. Items Pending Confirmation (Blockers)

| # | Item | Waiting on | Status |
|---|---|---|---|
| 1 | Teammates' GitHub usernames (for access) | Alfos | ⏳ |
| 2 | Feature prioritisation (L1/L2/L3 confirmation) | Alfos | ⏳ |
| 3 | Real marks samples | Alfos | ⏳ |
| 4 | Marking criteria email | Alfos (today) | ⏳ |
| 5 | Key iLearn page information (competition timeline) | Xing + Hermes | ⏳ |
| 6 | Reference documents (for lesson planner) | Alfos | ⏳ |
| 7 | Rename list confirmation | Team | ⏳ |

---

## Appendix: Design Avoid Checklist (for acceptance, 17 items)
purple-blue gradient / gradient hero text / emoji in headings / Inter everywhere / colored border cards / glassmorphism / low-contrast dark mode / 3 icon boxes in a row / badge above headline / lucide icons everywhere / untouched shadcn / fade-in-scroll + cursor beam / hover fade buttons / inconsistent spacing / em dashes / buzzword copy / serif italic accents / Space Grotesk+Instrument Serif / grain over gradient

**Our replacements**: solid colours (paper / ink / marking red), system font stack, no icons, exam-paper layout, state-driven motion, concrete language, zero em dashes.
