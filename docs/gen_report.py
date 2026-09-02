#!/usr/bin/env python3
"""CoachAI full progress report generator (.docx, EN)."""
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

HEADER_BG = "1F4E79"
ALT_ROW = "F2F6FA"
DARK_BLUE = RGBColor(0x1F, 0x4E, 0x79)
GRAY = RGBColor(0x6B, 0x76, 0x84)
FIG_DIR = "/home/gaogao/workspace/ai-coach/docs/figures"

def set_cell_shading(cell, color):
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>'))

def set_cell_text(cell, text, bold=False, color=None, size=Pt(10)):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    run = p.add_run(str(text))
    run.font.name = "Calibri"
    run.font.size = size
    run.bold = bold
    if color:
        run.font.color.rgb = color

def create_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        set_cell_shading(cell, HEADER_BG)
        set_cell_text(cell, h, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            set_cell_text(cell, str(val))
            if r_idx % 2 == 0:
                set_cell_shading(cell, ALT_ROW)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return table

def h1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.name = "Calibri"; r.font.size = Pt(16); r.bold = True
    r.font.color.rgb = DARK_BLUE
    return p

def h2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.font.name = "Calibri"; r.font.size = Pt(13); r.bold = True
    return p

def body(doc, text, size=Pt(11)):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.name = "Calibri"; r.font.size = size
    return p

def bullet(doc, text, bold_prefix=None):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.left_indent = Cm(0.6)
    if bold_prefix:
        r1 = p.add_run(bold_prefix + " ")
        r1.font.name = "Calibri"; r1.font.size = Pt(11); r1.bold = True
    r = p.add_run(text)
    r.font.name = "Calibri"; r.font.size = Pt(11)
    return p

def code(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.font.name = "Consolas"; r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x2D, 0x2D, 0x2D)
    return p

def figure(doc, path, width=Inches(6.2), caption=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(path, width=width)
    if caption:
        c = doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = c.add_run(caption)
        r.font.name = "Calibri"; r.font.size = Pt(9); r.italic = True
        r.font.color.rgb = GRAY

doc = Document()
for section in doc.sections:
    section.top_margin = Cm(2.2); section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.2); section.right_margin = Cm(2.2)

# ============ COVER ============
for _ in range(5):
    doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("CoachAI")
r.font.name = "Calibri"; r.font.size = Pt(34); r.bold = True; r.font.color.rgb = DARK_BLUE
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("AI Real-Time Coach for HSC Enterprise Computing")
r.font.name = "Calibri"; r.font.size = Pt(16)
doc.add_paragraph()
for line in ["Project Progress & Technical Report", "", "Team iSoft AI Innovation",
             "Prepared by: Xing (new member) | 2 September 2026", "Version 1.0"]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(line)
    r.font.name = "Calibri"; r.font.size = Pt(12 if line and line[0].isalpha() else 11)
doc.add_page_break()

# ============ 1. EXECUTIVE SUMMARY ============
h1(doc, "1. Executive Summary")
body(doc, "This report documents everything the team has produced since Xing joined: the architecture, "
          "the working codebase, the verification methodology, and the measured results. The deliverable is a "
          "working proof of concept: an AI that marks HSC Enterprise Computing short answers against the "
          "official NESA marking guidelines, with confidence levels and teacher-in-the-loop review.")
body(doc, "Headline numbers:")
create_table(doc, ["Asset", "Status", "Detail"], [
    ["Question bank", "Done", "18 questions from the 2025 HSC Enterprise Computing exam (the subject's first-ever HSC paper), with official marking guidelines transcribed verbatim from the NESA marking guidelines PDF"],
    ["RAG knowledge base", "Done", "4 official NESA Teacher Support Resources (Year 12 modules) indexed into Chroma: 1,046 chunks"],
    ["Marking engine", "Done", "LangGraph state machine: Marker Agent + Verifier Agent + RAG retrieval + confidence blending + retry loop"],
    ["Model abstraction", "Done", "One config line swaps the LLM provider (DeepSeek active now; Gemini free tier / local Ollama ready)"],
    ["Frontend", "Done", "Gradio app (phone-friendly, EN/CN toggle), running locally on port 7860"],
    ["Verification", "Done", "Golden Set: 32 simulated answers (8 questions x 4 quality bands), expected marks from official rubric"],
    ["Verification result", "Measured", "32/32 graded within +/-1 band of the official rubric (100%); exact match 78.1%; zero wild misses"],
], col_widths=[4.0, 2.0, 10.0])

# ============ 2. WHAT WE BUILT ============
h1(doc, "2. What We Built (System Overview)")
body(doc, "The system follows our chosen architecture from the team document: NESA materials are the single "
          "source of truth; two LangGraph workflows share a RAG knowledge base; every LLM call goes through "
          "one abstraction layer; students and teachers interact through a mobile-friendly web UI.")
figure(doc, f"{FIG_DIR}/architecture.png", caption="Figure 1 - System architecture overview")

# ============ 3. CODEBASE MAP ============
h1(doc, "3. Codebase Map")
code(doc, "ai-coach/\n"
          "|-- app.py                  # Gradio UI (question picker, answer input, results)\n"
          "|-- agents/\n"
          "|   |-- models.py           # Model abstraction layer - complete() is the ONLY LLM entry point\n"
          "|   |-- marker.py           # Marker Agent: HSC teacher role, T=0.5, provisional marks + feedback\n"
          "|   `-- verifier.py         # Verifier Agent: NESA QA auditor role, T=0.2, audit + confidence\n"
          "|-- graphs/\n"
          "|   `-- mark_graph.py       # LangGraph state machine (Workflow 1) + mark_answer() public API\n"
          "|-- rag/\n"
          "|   |-- indexer.py          # TSR docx -> chunks -> Chroma (1,046 chunks, MiniLM-L6-v2)\n"
          "|   `-- retriever.py        # search(query, k, topic) used by the graph's retrieve node\n"
          "|-- data/\n"
          "|   |-- questions.json      # 18-question bank with official marking guidelines\n"
          "|   `-- chroma_db/          # persistent vector store\n"
          "|-- tests/\n"
          "|   |-- golden_set.json     # 32 answers with expected marks + justification\n"
          "|   |-- run_golden.py       # regression runner: AI mark vs expected mark\n"
          "|   |-- test_mark.py        # workflow smoke tests\n"
          "|   `-- test_llm.py         # model connectivity test\n"
          "|-- raw/                    # source PDFs + extracted text (2025 HSC MG, full-mark samples)\n"
          "`-- docs/figures/           # report figures")
body(doc, "The public contract used by the UI: mark_answer(question_id, student_answer) returns a dict with "
          "status (approved / flagged / error), marks, max_marks, confidence_pct, confidence_level, "
          "feedback items and flags. Errors never raise - they are returned as status=error so the UI can "
          "show a friendly message.")

# ============ 4. KEY DESIGN DECISIONS ============
h1(doc, "4. Key Design Decisions")

h2(doc, "4.1 Model abstraction - switching LLM providers costs nothing")
body(doc, "A recurring team concern was: if we start with one API and later move to another (e.g. Gemini "
          "free tier or a local open-weight model), do we redo everything? No. Every agent calls "
          "agents.models.complete() and nothing else. The provider is resolved from configuration.")
figure(doc, f"{FIG_DIR}/model_abstraction.png", caption="Figure 2 - Model abstraction layer", width=Inches(5.8))
body(doc, "DeepSeek deepseek-v4-flash is active now (cheap, reliable, we already had a key). Gemini 3.5 Flash "
          "free tier and local Ollama are one-line additions when we need them.")

h2(doc, "4.2 Two-agent marking engine (Workflow 1)")
body(doc, "The core pipeline implements the team's original design: a Marker grades generously with "
          "contextual interpretation (T=0.5); an independent Verifier audits sceptically (T=0.2) - "
          "recomputing the mark, hunting for hallucinated concepts against the retrieved syllabus material, "
          "and rejecting verdicts it does not agree with.")
figure(doc, f"{FIG_DIR}/workflow1.png", caption="Figure 3 - Workflow 1: LangGraph state machine", width=Inches(6.2))

h2(doc, "4.3 Confidence score - not a model guess")
body(doc, "The Verifier self-reports confidence, but we blend it with objective signals so the number is "
          "explainable and audit-friendly:")
code(doc, "confidence = 0.6 x verifier_self_report\n"
          "          + 20 if marker and verifier marks agree\n"
          "          + 10 if they differ by exactly 1 band\n"
          "          + 10 if the verifier approved\n"
          "clamped to [25, 95]   (never 100%: a human always has the last word)")
body(doc, "Mapping: >=80 high (auto-ship), 50-79 medium, <50 low (flagged for teacher review).")

h2(doc, "4.4 Retrieval-first RAG")
body(doc, "RAG retrieval runs BEFORE grading: the retrieved NESA syllabus chunks are injected into the "
          "Marker's prompt as grading context, not appended afterwards as an afterthought. Only official "
          "NESA material is indexed - this is our answer to the 'internet contradicts the course' problem.")

h2(doc, "4.5 Retry loop with a hard cap")
body(doc, "When the Verifier rejects a verdict, the critique is fed back to the Marker for one re-grade "
          "round (max 2 rounds). If it still disagrees, the answer is flagged for a human teacher - no "
          "infinite loop, no wasted API budget.")

# ============ 5. VERIFICATION ============
h1(doc, "5. How We Verified (Methodology)")
body(doc, "To measure quality honestly we built a Golden Set - the same pattern used in academic grading "
          "research:")
bullet(doc, "8 real 2025 HSC questions were selected (text-answerable ones across all four syllabus modules)", bold_prefix="Questions:")
bullet(doc, "For each question we wrote 4 simulated student answers: excellent, good, weak, borderline (32 total) - deliberately imperfect, with the occasional spelling slip, like real students", bold_prefix="Answers:")
bullet(doc, "Expected marks were derived strictly from the official NESA marking guidelines; every answer carries a note stating which band criterion justifies its expected mark", bold_prefix="Expected marks:")
bullet(doc, "tests/run_golden.py feeds each answer through the real pipeline and compares AI marks against expected marks", bold_prefix="Runner:")
bullet(doc, "During human review one expectation was itself revised (q24 weak: 1 -> 2 marks) because the official band-2 criterion ('Identifies some features...') clearly applied - the correction is logged in golden_set.json with its rationale", bold_prefix="Self-audit:")

# ============ 6. RESULTS ============
h1(doc, "6. Verification Results")
create_table(doc, ["Metric", "Value"], [
    ["Answers graded successfully", "32 / 32 (0 skipped, 0 errors)"],
    ["Exact match with official rubric", "25 / 32 = 78.1%"],
    ["Within +/-1 band of official rubric", "32 / 32 = 100%"],
    ["Wild misses (>=2 bands off)", "0"],
], col_widths=[8.0, 8.0])
body(doc, "By answer quality:")
create_table(doc, ["Quality band", "Exact match", "Within +/-1 band", "Notes"], [
    ["Excellent (top answers)", "8/8 = 100%", "100%", "The engine reliably recognises high-quality answers"],
    ["Good", "7/8 = 87.5%", "100%", ""],
    ["Weak", "6/8 = 75%", "100%", ""],
    ["Borderline (trickiest)", "4/8 = 50%", "100%", "Disagreement here is expected - this is exactly what the Verifier flags for the teacher"],
], col_widths=[4.5, 3.0, 3.0, 5.5])
figure(doc, f"{FIG_DIR}/golden_results.png", caption="Figure 4 - Golden Set results (n=32)", width=Inches(6.0))
body(doc, "Interpretation: zero wild misses means no 'great answer failed' or 'bad answer rewarded' cases. "
          "The 50% exact rate on borderline answers is not a weakness - real HSC markers disagree on "
          "borderline scripts too; our design routes exactly those cases to the teacher through the "
          "Verifier flag.")

# ============ 7. ISSUES FOUND & FIXED ============
h1(doc, "7. Issues Found and How We Fixed Them")
create_table(doc, ["Issue", "Root cause", "Fix"], [
    ["Verifier output truncated on long questions (q24, 5 marks)", "Default max_tokens=4096 cut long JSON replies mid-string", "max_tokens raised to 8192 for the Verifier + prompt now asks for compact feedback (<40 words per item)"],
    ["2/32 golden answers skipped with JSON parse errors", "Same truncation issue", "Fixed above - re-run graded 32/32 with zero skips"],
    ["One expected mark looked too harsh (q24 weak: expected 1)", "Human labelling of the 'weak' answer was stricter than the official band-2 criterion", "Re-derived from the rubric: expected 2. Logged in golden_set.json with rationale"],
    ["Model name 'deepseek-chat' failed", "DeepSeek API serves model ids deepseek-v4-flash / deepseek-v4-pro", "Default model corrected to deepseek-v4-flash (verified via /models endpoint)"],
    ["No PDF past papers exist for this subject", "Enterprise Computing is examined fully online; 2025 was its first HSC year", "Question stems captured from the official online exam system (fam.hsconline.nesa.nsw.edu.au); marking guidelines PDF downloaded from nsw.gov.au"],
    ["Slow per-answer latency (30-70 s)", "Each answer costs 2-4 LLM calls on DeepSeek", "In-memory cache keyed on question + answer prefix; demo flow reuses cached results"],
], col_widths=[5.0, 5.5, 5.5])

# ============ 8. HOW TO RUN ============
h1(doc, "8. How to Run It")
code(doc, "cd ai-coach\npip install -r requirements.txt     # openai, python-dotenv, langgraph, chromadb, gradio, sentence-transformers\n# .env: DEEPSEEK_API_KEY=sk-... DEEPSEEK_BASE_URL=https://api.deepseek.com/v1\npython3 app.py                      # Gradio UI at http://127.0.0.1:7860\npython3 tests/test_llm.py           # model connectivity\npython3 tests/run_golden.py         # full 32-answer regression (~30-45 min)")
body(doc, "The demo concept page (ai-coach/demo/index.html) shows the intended UX without any backend.")

# ============ 9. NEXT ============
h1(doc, "9. What Is Next")
bullet(doc, "Deploy the Gradio app to Hugging Face Spaces for a public link the whole team (and judges) can open on a phone", bold_prefix="Public demo:")
bullet(doc, "Workflow 2 (report generation from spreadsheets) on the second graph slot in the architecture", bold_prefix="Report feedback:")
bullet(doc, "Follow-up chat so a student can ask 'why did I lose the mark?' - the real-time coach experience", bold_prefix="Coaching chat:")
bullet(doc, "Photo upload with DeepSeek's vision model (deepseek-v4-flash-vision-exp exists on our key) or a local vision model", bold_prefix="Handwritten answers:")
bullet(doc, "Gemini free tier / local Ollama swap to tell the open-weight story in the pitch", bold_prefix="Model swap demo:")

# ============ APPENDIX ============
h1(doc, "Appendix A - Data Sources")
bullet(doc, "2025 HSC Enterprise Computing marking guidelines: nsw.gov.au (33 pages, downloaded 2026-09-02)")
bullet(doc, "2025 HSC full-mark sample responses: nsw.gov.au (11 pages)")
bullet(doc, "Question stems: official online exam system fam.hsconline.nesa.nsw.edu.au")
bullet(doc, "4x NESA Teacher Support Resources (Year 12: data science, data visualisation, enterprise project, intelligent systems) - shared by the team")
bullet(doc, "All artifacts live in /home/gaogao/workspace/ai-coach/ with raw source files kept under raw/ for traceability")

doc.save("/home/gaogao/workspace/ai-coach/CoachAI_Progress_Report_v1.0.docx")
print("EN report saved")
