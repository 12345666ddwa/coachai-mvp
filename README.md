# CoachAI — AI Real-Time Coach for HSC Enterprise Computing

An AI that marks HSC short answers against the **official NESA marking guidelines**,
with confidence levels and teacher-in-the-loop review.

- **Concept demo (playable):** open the homepage of this site, or `demo/index.html`
- **Full progress report:** `CoachAI_Progress_Report_v1.0.docx`
- **Verification results:** `tests/GOLDEN_REPORT.md`

## Status

| Asset | Status |
|---|---|
| Question bank | 18 questions, 2025 HSC Enterprise Computing (first-ever HSC paper for this subject) + official marking guidelines |
| RAG knowledge base | 4 official NESA Teacher Support Resources indexed (1,046 chunks, Chroma) |
| Marking engine | LangGraph: Marker Agent + Verifier Agent + retrieval + confidence + retry |
| Frontend | Gradio app (EN/CN), phone-friendly |
| Golden Set | 32 answers x 4 quality bands; **32/32 within +/-1 band of official rubric (100%), exact 78.1%, zero wild misses** |

## Architecture (summary)

NESA materials -> vector store -> [RAG] -> LangGraph state machine:
`load question -> retrieve -> grade (Marker, T=0.5) -> verify (Verifier, T=0.2) -> approve / retry (<=2) / flag for teacher`

All LLM calls go through `agents/models.py complete()` — swapping providers (DeepSeek now,
Gemini free tier / local Ollama later) is one config line.

See `docs/figures/` for architecture diagrams.

## Run it

```bash
pip install -r requirements.txt
# .env: DEEPSEEK_API_KEY=... DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
python3 app.py                # Gradio UI at http://127.0.0.1:7860
python3 tests/run_golden.py   # full 32-answer regression
```

## Data sources (traceable)

- 2025 HSC Enterprise Computing marking guidelines (nsw.gov.au, official)
- 2025 HSC full-mark sample responses (nsw.gov.au, official)
- Question stems: official NESA online exam system (fam.hsconline.nesa.nsw.edu.au)
- 4x NESA Teacher Support Resources (Year 12 modules) — provided by the team
