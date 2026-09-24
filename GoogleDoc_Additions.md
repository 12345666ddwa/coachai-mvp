# CoachAI - Copy-paste updates for the shared Google Doc
# (iSoft AI Innovation - ideation doc)

====================================================================
PART A - IN-PLACE UPDATES (3 small edits so the doc stays truthful)
====================================================================

A1. In "Tools" section, replace this line:
    "Gemini free api"
  with:
    "Gemini free api [STATUS: DeepSeek deepseek-v4-flash is active via the model abstraction layer - Gemini free tier / local Ollama are one-line swaps, no code changes]"

A2. In "Planning" section, after the Hugging Face Spaces line, append:
    "[STATUS 4 Sep 2026: HF free tier no longer hosts Gradio apps (now PRO-only). We are live via a Cloudflare Tunnel; a permanent host (HF PRO or Render) remains an optional upgrade.]"
    Also next to "Uses Gemini free API (gemini 3.5 FLASH)" append:
    "[STATUS: using DeepSeek deepseek-v4-flash - same OpenAI-compatible pattern, one-line swap to Gemini]"

A3. In "Note" section, after "Potentially, we will not even need to do any fine tuning and instead just the prompt you are a [teacher / quality assurance auditor]"
  append:
    "[CONFIRMED IN BUILD: no fine-tuning was needed. 32-answer regression: 78.1% exact match with official rubric, 100% within +/-1 band, zero wild misses. Details in the build log below.]"

====================================================================
PART B - APPEND AT THE END OF THE DOC
====================================================================

--------------------------------------------------------------------------------
BUILD STATUS - 4 September 2026 (working MVP, implemented by Xing with team review)
--------------------------------------------------------------------------------

LIVE LINKS
- Real AI marking demo (try it on your phone): https://pci-wav-hardwood-fix.trycloudflare.com
  (served from the team laptop via temporary tunnel - online when the laptop is on; ask Xing to restart if dead)
- Concept demo (static, always online): https://12345666ddwa.github.io/coachai-mvp/
- Source code + full progress report (Word): https://github.com/12345666ddwa/coachai-mvp
  (report docx also shared in the chat - page 2 has clickable links)

IDEA -> BUILD STATUS MAP (what the doc planned vs what exists now)
| Doc idea | Build status | Evidence |
|---|---|---|
| Workflow 1: short-answer marking | DONE and running | LangGraph state machine, live demo |
| Marker Agent + Verifier Agent (2 agents) | DONE as specified (Marker T=0.5, Verifier T=0.2, Verifier returns strict JSON with final_marks / is_approved / confidence) | agents/marker.py, agents/verifier.py |
| RAG over NESA TSRs | DONE - 4 TSRs indexed, 1,046 chunks (Chroma + MiniLM embeddings) | rag/indexer.py, rag/retriever.py |
| Question bank from official HSC paper | DONE - 18 questions from the 2025 HSC paper (the subject's first HSC exam) with official marking guidelines verbatim from the NESA PDF | data/questions.json |
| Confidence intervals | DONE - blended formula (verifier self-report x0.6 + marker/verifier agreement + approval), capped 95 / floored 25; levels high/medium/low | graphs/mark_graph.py |
| "2nd gen AI verifies output" | DONE - Verifier is the second independent pass; disagreements trigger a re-grade (max 2 rounds) then flag for teacher | graphs/mark_graph.py |
| Query_data / Google Sheets (Workflow 2) | NEXT - Workflow 2 architecture slot is reserved (report_graph) | - |
| Lesson plans / student interface (Workflow 3+) | FUTURE | - |
| Open-weight models + run on phone | Partially met - cloud model now (open-weight family); local open-weight model is the documented next step (fine-tuning roadmap, see below) | - |

ONE DELIBERATE DIFFERENCE FROM THE DOC'S ARCHITECTURE DIAGRAM
The doc's diagram shows: Grader -> RAG Retriever -> Verifier.
We implemented: RAG retrieval BEFORE grading (load -> retrieve -> grade -> verify).
Why: the Marker needs the retrieved rubric/syllabus material IN its prompt to grade well; retrieving afterwards can only check, not guide. The Verifier still sees the same retrieved docs for its hallucination check.

VERIFICATION (Golden Set - our pitch ammunition)
Method: 8 real 2025 HSC questions x 4 quality bands = 32 simulated student answers; expected marks derived strictly from the official NESA marking guidelines (one expectation self-audited and corrected: q24 weak 1 -> 2, logged in golden_set.json).
| Metric | Result |
|---|---|
| Graded successfully | 32/32 (0 skipped) |
| Exact match with official rubric | 25/32 = 78.1% |
| Within +/-1 band | 32/32 = 100% |
| Wild misses (>=2 bands off) | 0 |
By quality band: excellent 100% exact / good 87.5% / weak 75% / borderline 50% (borderline all within +/-1 band - and borderline disagreement is exactly what gets flagged to the teacher by design).
One-line judge quote: "32 answers, zero wild misses, 100% within +/-1 band of the official rubric."

FINE-TUNING CLARIFICATION (answers the "what was it trained on" question)
- No fine-tuning (0 epochs, by design). The model is DeepSeek v4-flash, a general-purpose pretrained LLM that never saw HSC material in training.
- HSC knowledge enters at inference time: (1) question bank with official marking guidelines; (2) RAG injects the 4 TSRs' relevant chunks into the prompt. 5 official documents in total.
- Evidence: ACM 2025 (open-weight LLMs + rubric prompts grade competitively without fine-tuning) + our own 32-answer regression above.
- Roadmap if we add it later (offline deployment): grow labels to ~300 -> LoRA/QLoRA on a small open-weight base -> re-run the same regression as the acceptance gate -> Marker runs local, Verifier stays on the cloud model. Existing 32 answers stay reserved as the held-out test set (never train on them).

KEY ENGINEERING DECISIONS (worth logging here)
1. Model abstraction layer first - no provider lock-in (DeepSeek today, Gemini/Ollama later = one config line)
2. Retrieval-first RAG (see difference note above)
3. Verifier T=0.2 vs Marker T=0.5 - deliberate personality split
4. Retry capped at 2 rounds then flag for teacher - never an infinite loop
5. Confidence never 100% - a human always has the last word
6. No fine-tuning in MVP - evidence + regression show it is unnecessary; roadmap exists

NEXT STEPS / TASK SUGGESTIONS
| Task | Notes |
|---|---|
| Everyone: try the live demo, send UI/UX feedback | 30-60 s per answer; refresh to see latest UI |
| Read the full progress report | Word doc in chat; page 2 = clickable links |
| Decide on permanent public host | HF PRO (~USD 9/mo) or free Render - only needed if the laptop is not present |
| Workflow 2 (report generation + student tracker) | Architecture slot ready; needs a volunteer |
| Coaching follow-up chat ("why did I lose the mark?") | Differentiator feature; needs a volunteer |
| Handwritten answer photos | DeepSeek vision model exists on our key (deepseek-v4-flash-vision-exp) |
| UI polish per team feedback | Iterating now (see live demo) |
