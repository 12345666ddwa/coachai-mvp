# CoachAI - Suggested additions to the shared team doc

Copy-paste ready. Figures can be inserted from the desktop folder `ai-coach-MVP提案/figures/` (or from the GitHub repo `docs/figures/`).

---

## 1) Status banner (top of the doc)

**BUILD STATUS (2 Sep 2026): working MVP - live demo available**
- Live AI marking demo (real engine): https://pci-wav-hardwood-fix.trycloudflare.com
- Concept demo (static): https://12345666ddwa.github.io/coachai-mvp/
- Source code + full progress report: https://github.com/12345666ddwa/coachai-mvp
- Full progress report (Word): CoachAI_Progress_Report_v1.0.docx (shared in the chat)

Note: the live demo is served from a laptop via a temporary tunnel - online whenever the laptop is running. Ask Xing to restart it if the link stops working.

## 2) Architecture (replaces the draft ASCII diagram)

[Insert Figure: architecture.png - full system overview]
[Insert Figure: workflow1.png - Workflow 1 state machine]

Summary in text:
- Two LangGraph workflows (mark_graph active, report_graph next) share one RAG knowledge base (1,046 chunks from the 4 TSRs) and one model abstraction layer.
- All LLM calls go through agents/models.py complete() - swapping providers (DeepSeek now; Gemini free / local Ollama later) is one config line.

## 3) What is built (status table)

| Asset | Status | Detail |
|---|---|---|
| Question bank | DONE | 18 questions from the 2025 HSC exam (first-ever HSC paper for Enterprise Computing) + official marking guidelines verbatim from the NESA PDF |
| RAG knowledge base | DONE | 4 TSRs indexed (1,046 chunks, Chroma, MiniLM embeddings) |
| Marking engine | DONE | LangGraph: load -> retrieve -> grade (Marker T=0.5) -> verify (Verifier T=0.2) -> approve / retry (<=2) / flag for teacher |
| Confidence | DONE | Blended formula (self-report x 0.6 + agreement bonus + approval), capped at 95, floored at 25 |
| Frontend | DONE | Gradio app (EN/CN), full question display, phone-friendly |
| Report feedback (Workflow 2) | NEXT | Spreadsheet -> trends -> NESA-aligned report comments |
| Public hosting | PARTIAL | Cloudflare Tunnel live now; permanent host optional (HF Spaces now requires PRO for Gradio) |

## 4) Verification results (Golden Set - this is our pitch ammunition)

Method: 8 real 2025 HSC questions x 4 quality bands = 32 simulated student answers; expected marks derived from the official NESA marking guidelines (with one self-audited correction logged: q24 weak 1 -> 2).

| Metric | Result |
|---|---|
| Graded successfully | 32/32 (0 skipped) |
| Exact match with official rubric | 25/32 = 78.1% |
| Within +/-1 band | 32/32 = 100% |
| Wild misses (>=2 bands off) | 0 |

By quality band: excellent 100% exact, good 87.5%, weak 75%, borderline 50% (all within +/-1 band).

One-line takeaway for judges: "32 answers, zero wild misses, 100% within +/-1 band of the official rubric - and borderline disagreement is exactly what gets flagged to the teacher by design."

## 5) Training / fine-tuning clarification (answering Alfos's question)

- No fine-tuning (0 epochs, by design). Model = DeepSeek v4-flash, a general-purpose pretrained LLM that never saw HSC material in training.
- HSC knowledge enters at inference time: (1) question bank with official marking guidelines; (2) RAG injects the 4 TSRs' relevant chunks into the prompt. 5 official documents total.
- Evidence: ACM 2025 (open-weight LLMs + rubric prompts grade competitively without fine-tuning) + our own 32-answer regression above.
- Fine-tuning roadmap documented (report section 4.7): grow labels to ~300 -> LoRA on a small open-weight base -> same regression as acceptance gate -> Marker runs local, Verifier stays on the cloud model. Timing: after competition core is stable.

## 6) Key decisions we made (for the doc's decision log)

1. Model abstraction layer first - no provider lock-in (cost us one afternoon, saves everything later)
2. Retrieval-first RAG (rubric + syllabus chunks go INTO the marker prompt, not appended after)
3. Verifier temperature 0.2 vs Marker 0.5 - deliberate personality split
4. Retry capped at 2 rounds, then flag for teacher - never an infinite loop
5. Confidence never 100% - a human always has the last word (teacher-in-the-loop)
6. No fine-tuning in MVP - evidence + our regression show it is unnecessary; roadmap exists for offline mode

## 7) Next steps / task suggestions

| Task | Owner suggestion | Notes |
|---|---|---|
| Try the live demo + report UI feedback | All members | Link at top; 30-60 s per answer |
| Read the full progress report | All members | Word doc in chat |
| Decide: permanent public host (optional) | Team decision | ~USD 9/mo HF PRO or free Render (needs account) |
| Workflow 2 (report generation) | Volunteer | Architecture slot ready |
| Coaching follow-up chat | Volunteer | Differentiator feature |
| Handwritten answer photos | Volunteer | DeepSeek vision model available on our key |
