#!/usr/bin/env python3
"""Generate MVP Technical Proposal as .docx (EN main + CN archive)."""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
import shutil, os

HEADER_BG = "1F4E79"
ALT_ROW = "F2F6FA"
DARK_BLUE = RGBColor(0x1F, 0x4E, 0x79)
GRAY = RGBColor(0x2D, 0x2D, 0x2D)
SONG = "宋体"
HEI = "黑体"

def set_cell_shading(cell, color):
    cell._tc.get_or_add_tcPr().append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color}"/>'))

def set_cell_text(cell, text, bold=False, color=None, size=Pt(10), font="Calibri"):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.space_before = Pt(2)
    run = p.add_run(str(text))
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
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
        set_cell_text(cell, h, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF), size=Pt(10))
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            set_cell_text(cell, str(val), size=Pt(10))
            if r_idx % 2 == 0:
                set_cell_shading(cell, ALT_ROW)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return table

def add_h1(doc, text, font="Calibri"):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(text)
    r.font.name = font
    r._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    r.font.size = Pt(16)
    r.bold = True
    r.font.color.rgb = DARK_BLUE
    return p

def add_h2(doc, text, font="Calibri"):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.name = font
    r._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    r.font.size = Pt(14)
    r.bold = True
    return p

def add_h3(doc, text, font="Calibri"):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.font.name = font
    r._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    r.font.size = Pt(12)
    r.bold = True
    return p

def add_body(doc, text, font="Calibri", size=Pt(11), spacing=1.15, space_after=Pt(6)):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = spacing
    p.paragraph_format.space_after = space_after
    r = p.add_run(text)
    r.font.name = font
    r._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    r.font.size = size
    return p

def add_bullet(doc, text, font="Calibri", size=Pt(11), spacing=1.15):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = spacing
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.left_indent = Cm(0.6)
    r = p.add_run(text)
    r.font.name = font
    r._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    r.font.size = size
    return p

def add_code_block(doc, lines):
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(line)
        r.font.name = "Consolas"
        r.font.size = Pt(8.5)
        r.font.color.rgb = GRAY
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

def add_cover(doc, title, subtitle, meta_lines):
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(title)
    r.font.name = "Calibri"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), HEI)
    r.font.size = Pt(26)
    r.bold = True
    r.font.color.rgb = DARK_BLUE
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    r = p.add_run(subtitle)
    r.font.name = "Calibri"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), SONG)
    r.font.size = Pt(14)
    for i in range(3):
        doc.add_paragraph()
    for line in meta_lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(line)
        r.font.name = "Calibri"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), SONG)
        r.font.size = Pt(12)
    doc.add_page_break()

def setup_page(doc):
    for section in doc.sections:
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.54)
        section.right_margin = Cm(2.54)

# ============ ENGLISH VERSION ============
def build_en():
    doc = Document()
    setup_page(doc)
    add_cover(doc,
        "MVP Technical Proposal",
        "AI Real-Time Coach for HSC Qualitative Subjects",
        ["Team iSoft AI Innovation", "Prepared by: Xing (new member)", "26 August 2026", "Version 0.1"])

    add_h1(doc, "1. Executive Summary")
    add_body(doc, "This proposal defines the smallest working version of our idea: an AI coach that marks HSC short-answer responses against official NESA marking guidelines. It returns a mark, a confidence level, and personalised feedback. Teachers verify the AI work. We deliver a demo-ready MVP in about 2 weeks.")

    add_h1(doc, "2. MVP Scope")
    add_h2(doc, "2.1 In scope (pipeline 1 only, one subject)")
    create_table(doc,
        ["Item", "Detail"],
        [["Subject", "ONE HSC qualitative subject (candidate: Enterprise Computing, with public past papers and official marking guidelines)"],
         ["Questions", "5-10 real past-paper short-answer questions + official NESA marking guidelines"],
         ["Student flow", "Type or paste an answer -> get mark / max, confidence level, specific feedback, 1-2 practice questions for the weakest rubric band"],
         ["Teacher flow", "See flagged answers -> accept / edit / reject the AI mark (one click)"],
         ["Device", "Mobile-friendly web page. Works in a phone browser. Satisfies the 'runs on phone' requirement for the demo without a native app"]],
        col_widths=[3.5, 12.5])
    add_h2(doc, "2.2 Out of scope (later phases)")
    add_bullet(doc, "Report generation (pipeline 2), lesson-plan generation (pipeline 3), transcript feedback (pipeline 4)")
    add_bullet(doc, "Fine-tuning, vision capability, native iOS/Android apps, multi-subject support")
    add_bullet(doc, "Real classroom deployment. We demo, we do not ship.")

    add_h1(doc, "3. Tech Choices")
    add_h2(doc, "3.1 Model strategy: two tracks (key decision)")
    create_table(doc,
        ["Track", "What", "Why", "Cost"],
        [["A - Hosted open-weight API (now)", "Qwen3 / DeepSeek / Llama family via any OpenAI-compatible API", "Demo-quality marking today. Zero GPU, zero setup. Validates rubric-conditioned marking fastest", "Under AUD 5 for the whole demo"],
         ["B - Local small model (next)", "Small open-weight model (Qwen3-4B / Gemma 4 small / Llama 3.2 3B, GGUF Q4) via Ollama", "Proves the 'runs on a phone-class device' story. Same code, same prompts, only the endpoint URL changes", "Free"]],
        col_widths=[3.6, 5.0, 5.8, 2.4])
    add_body(doc, "Why two tracks: decouple 'does the idea work?' (Track A, this week) from 'can we deploy it small?' (Track B, after marking quality is confirmed). The open-weight requirement in our brief is satisfied either way.")
    add_h2(doc, "3.2 Marking engine: three-pass architecture (the core)")
    add_code_block(doc, [
        "Pass 1  GRADER   -> rubric-conditioned prompt: question + official NESA marking",
        "                   guidelines + example answers -> mark + band-by-band justification",
        "Pass 2  VERIFIER -> independent second pass (different model, or same model with",
        "                   different temperature/seed) re-marks the answer",
        "        (this is the '2nd gen AI verifies output' idea from our doc)",
        "Pass 3  FEEDBACK -> writes specific, kind, actionable feedback + 1-2 practice",
        "                   questions aimed at the student's weakest band",
    ])
    add_h3(doc, "Confidence interval (simple, honest version)")
    add_bullet(doc, "Pass 1 and Pass 2 agree -> high confidence, auto-accepted")
    add_bullet(doc, "Marks differ by 1 band -> medium confidence, teacher sees the disagreement")
    add_bullet(doc, "Marks differ by 2+ bands -> low confidence, flagged for teacher review")
    add_body(doc, "This is exactly the 'teachers only verify flagged/borderline questions' idea from our signoff. Published research supports it (see section 5).")
    add_h2(doc, "3.3 Knowledge base / RAG: the repository of truth")
    add_bullet(doc, "Index NESA marking guidelines + past papers + syllabus glossary into a vector DB (FAISS or Chroma, free, runs locally)")
    add_bullet(doc, "Retrieve the relevant rubric fragments per question and inject them into the prompt")
    add_bullet(doc, "Fixes the 'internet contradicts the course' problem: we only feed NESA materials, never generic web content")
    add_h2(doc, "3.4 Stack")
    create_table(doc,
        ["Layer", "Choice", "Why"],
        [["Frontend", "Single mobile-friendly HTML page (no framework)", "Fast, demoable on any phone"],
         ["Backend", "FastAPI (Python)", "Simple, the whole team can read it"],
         ["LLM access", "OpenAI-compatible endpoint", "One codebase works for Track A (hosted) and Track B (Ollama local)"],
         ["Data", "Google Sheets", "Matches the 'query_data' idea in our doc"],
         ["Repo", "GitHub", "Set up this week, no CI needed yet"]],
        col_widths=[3.2, 6.5, 6.5])

    add_h1(doc, "4. Architecture")
    add_code_block(doc, [
        "+-------------+   +------------------+   +---------------------------------+",
        "|  Phone /    |   |  FastAPI backend |   |  Pass 1 GRADER --------+         |",
        "|  laptop     +-->+  (Python)        +-->+  Pass 2 VERIFIER       +--> Mark  |",
        "|  browser    |   |                  |   |  Pass 3 FEEDBACK ------+   + CI  |",
        "+-------------+   +------------------+   +---------------+---------+",
        "                                                    | RAG",
        "                                      +-------------v------------+",
        "                                      | NESA docs (marking guides,",
        "                                      | past papers, glossary)   |",
        "                                      | FAISS/Chroma vector DB   |",
        "                                      +--------------------------+",
        "Teacher review page: accept / edit / reject flagged marks",
    ])

    add_h1(doc, "5. Evidence This Works (fills our External Research section)")
    add_bullet(doc, "SteLLA: Structured Grading System Using LLMs with RAG (arXiv:2501.09092). RAG + instructor rubric + reference answers significantly improves LLM short-answer grading accuracy. This is essentially our design, already validated.")
    add_bullet(doc, "Rubric-Conditioned LLM Grading: Alignment, Uncertainty (arXiv:2601.08843). Systematic evaluation of LLMs as rubric-based judges, including uncertainty estimation. Supports our confidence-interval approach.")
    add_bullet(doc, "Automatic Short Answer Grading with LLMs (ACM 2025). Open-weight LLMs with rubric prompts perform competitively without expensive fine-tuning. Supports our open-weight, no-fine-tuning-yet stance.")
    add_bullet(doc, "Competitor reference: marking.ai. Our differentiator stays 'real-time coaching + confidence + teacher-in-the-loop', not just marking.")

    add_h1(doc, "6. Timeline (2.5 weeks to demo)")
    create_table(doc,
        ["Days", "Milestone"],
        [["1-2", "GitHub repo up; pick subject + 5 questions + marking guidelines; single API call marks 1 answer"],
         ["3-5", "Three-pass engine + confidence logic; test on 10 mock answers (we write them, incl. 2 borderline ones)"],
         ["6-8", "RAG index of NESA docs; mobile-friendly web UI"],
         ["9-12", "Teacher review flow; polish; test on a real phone"],
         ["13+", "User test with 1-2 real students; collect feedback quotes for the pitch"]],
        col_widths=[2.5, 13.5])

    add_h1(doc, "7. Risks and Mitigations")
    create_table(doc,
        ["Risk", "Mitigation"],
        [["LLM marks unreliably on a hard question", "Verifier disagreement -> flag to teacher. Borderline cases stay manual by design"],
         ["API cost", "Track A is about AUD 5 total. Track B is free and local"],
         ["NESA material copyright / privacy", "We only use publicly available HSC materials. No real student data stored"],
         ["No real teacher contact", "Demo with mock teacher flow + genuine feedback from student testers"],
         ["Team capacity (known issue)", "Every member gets ONE small task. No single person is a bottleneck"]],
        col_widths=[7.0, 9.0])

    add_h1(doc, "8. Decisions Needed from the Team")
    add_bullet(doc, "1. Confirm subject: Enterprise Computing vs another HSC qualitative subject (needs past papers + marking guidelines available)")
    add_bullet(doc, "2. Confirm competition deadline and deliverable format (Alfos), so we can lock the timeline")
    add_bullet(doc, "3. Task split (suggested): backend + marking engine (1-2 people, Python); RAG + NESA data collection (1 person); frontend UI (1 person); pitch deck + demo script (1 person); user testing + feedback quotes (everyone, 1 hour each)")

    doc.save("/home/gaogao/workspace/ai-coach/MVP_Tech_Proposal_v0.1.docx")
    print("EN OK")

# ============ CHINESE VERSION ============
LQ = "\u201c"  # "
RQ = "\u201d"  # "

def build_cn():
    doc = Document()
    setup_page(doc)
    add_cover(doc,
        "MVP 技术选型提案",
        "AI 实时教练：面向 HSC 定性科目的教育 AI",
        ["团队：iSoft AI Innovation", "编写：高兴（新成员）", "2026年8月26日", "版本 0.1"])

    add_h1(doc, "一、核心摘要", font=HEI)
    add_body(doc, "本提案定义我们想法的最小可行版本：一个 AI 教练，按 NESA 官方评分标准批改 HSC 简答题，返回分数、置信度和个性化反馈，老师负责复核 AI 的批改。目标约 2 周内做出可演示的 MVP。", font=SONG, size=Pt(10.5), spacing=1.5)

    add_h1(doc, "二、MVP 范围", font=HEI)
    add_h2(doc, "2.1 范围内（仅管线 1，单一科目）", font=HEI)
    create_table(doc,
        ["项目", "说明"],
        [["科目", "一个 HSC 定性科目（候选：Enterprise Computing，有公开真题和官方评分标准）"],
         ["题目", "5-10 道真实真题简答题 + 官方 NESA 评分标准"],
         ["学生流程", "输入或粘贴答案 -> 得到：分数/满分、置信度、具体反馈、针对最弱评分项的 1-2 道练习题"],
         ["老师流程", "查看被标记的答案 -> 一键接受/修改/驳回 AI 分数"],
         ["设备", "手机友好网页，手机浏览器即可打开。满足演示用" + LQ + "手机运行" + RQ + "要求，无需原生 App"]],
        col_widths=[3.5, 12.5])
    add_h2(doc, "2.2 范围外（后续阶段）", font=HEI)
    add_bullet(doc, "报告生成（管线 2）、教案生成（管线 3）、阅读转写反馈（管线 4）", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "微调、视觉能力、原生 iOS/Android App、多科目支持", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "真实课堂部署。我们只做演示，不做正式上线。", font=SONG, size=Pt(10.5), spacing=1.5)

    add_h1(doc, "三、技术选型", font=HEI)
    add_h2(doc, "3.1 模型策略：双轨制（关键决策）", font=HEI)
    create_table(doc,
        ["轨道", "内容", "原因", "成本"],
        [["A - 云端开源权重 API（现在）", "Qwen3 / DeepSeek / Llama 系列，通过任意 OpenAI 兼容 API 调用", "今天就能获得演示级批改质量。零 GPU、零部署，最快验证" + LQ + "按评分标准批改" + RQ + "可行性", "整个 demo 不到 5 澳元"],
         ["B - 本地小模型（下一步）", "小规模开源模型（Qwen3-4B / Gemma 4 小号 / Llama 3.2 3B，GGUF Q4 量化），Ollama 运行", "证明" + LQ + "能跑在手机级设备" + RQ + "的故事。代码不变、提示词不变，只换接口地址", "免费"]],
        col_widths=[3.6, 5.0, 5.8, 2.4])
    add_body(doc, "为什么双轨：" + LQ + "想法能不能成" + RQ + "（A 轨，本周）和" + LQ + "能不能装进小设备" + RQ + "（B 轨，批改质量确认后）分开验证，互不拖累。Brief 要求的开源权重在任何一轨都满足。", font=SONG, size=Pt(10.5), spacing=1.5)
    add_h2(doc, "3.2 批改引擎：三遍架构（核心）", font=HEI)
    add_code_block(doc, [
        "第一遍 GRADER   -> 评分标准提示词：题目 + NESA 官方评分标准 + 范例答案",
        "                   -> 分数 + 逐评分档位依据",
        "第二遍 VERIFIER -> 独立第二遍批改（换模型，或同模型换温度和随机种子）",
        "        （对应文档里" + LQ + "第二代 AI 验证输出" + RQ + "的想法）",
        "第三遍 FEEDBACK -> 生成具体、友善、可执行的反馈 + 针对最弱评分档的 1-2 道练习题",
    ])
    add_h3(doc, "置信度（简单、诚实的版本）", font=HEI)
    add_bullet(doc, "第一遍与第二遍分数一致 -> 高置信度，自动通过", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "相差 1 个档位 -> 中置信度，老师可看到分歧", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "相差 2 个档位以上 -> 低置信度，标记给老师复核", font=SONG, size=Pt(10.5), spacing=1.5)
    add_body(doc, "这正是我们文档里" + LQ + "老师只复核被标记/边界题" + RQ + "的设想，且有已发表论文支撑（见第五节）。", font=SONG, size=Pt(10.5), spacing=1.5)
    add_h2(doc, "3.3 知识库 / RAG：真理库", font=HEI)
    add_bullet(doc, "把 NESA 评分标准 + 真题 + 教学大纲词汇表索引进向量库（FAISS 或 Chroma，免费，本地运行）", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "每题检索相关评分标准片段，注入提示词", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "从根上解决" + LQ + "网上信息与教材矛盾" + RQ + "：只喂 NESA 官方材料，绝不喂通用网络内容", font=SONG, size=Pt(10.5), spacing=1.5)
    add_h2(doc, "3.4 技术栈", font=HEI)
    create_table(doc,
        ["层", "选型", "原因"],
        [["前端", "单页移动友好 HTML（无框架）", "快，任何手机可演示"],
         ["后端", "FastAPI（Python）", "简单，全队都能读"],
         ["模型接入", "OpenAI 兼容接口", "同一套代码同时支持 A 轨（云端）和 B 轨（Ollama 本地）"],
         ["数据", "Google Sheets", "对应文档里的 query_data 想法"],
         ["代码仓库", "GitHub", "本周建好，暂不需要 CI"]],
        col_widths=[3.2, 6.5, 6.5])

    add_h1(doc, "四、架构图", font=HEI)
    add_code_block(doc, [
        "+-------------+   +------------------+   +---------------------------------+",
        "|  手机/电脑  |   |  FastAPI 后端    |   |  第一遍 GRADER --------+         |",
        "|  浏览器     +-->+  (Python)        +-->+  第二遍 VERIFIER       +--> 分数  |",
        "|             |   |                  |   |  第三遍 FEEDBACK ------+  +置信度 |",
        "+-------------+   +------------------+   +---------------+---------+",
        "                                                    | RAG",
        "                                      +-------------v------------+",
        "                                      | NESA 文档（评分标准、真题、",
        "                                      | 术语表）                  |",
        "                                      | FAISS/Chroma 向量库       |",
        "                                      +--------------------------+",
        "老师复核页：接受 / 修改 / 驳回被标记的分数",
    ])

    add_h1(doc, "五、可行性证据（正好补上 External research 空章节）", font=HEI)
    add_bullet(doc, "SteLLA：基于 RAG 的结构化 LLM 批改系统（arXiv:2501.09092）。RAG + 教师评分标准 + 参考答案显著提升 LLM 简答题批改准确率。本质就是我们的设计，已有验证。", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "Rubric-Conditioned LLM Grading: Alignment, Uncertainty（arXiv:2601.08843）。系统评估 LLM 作为评分标准裁判的表现，含不确定性估计，支撑我们的置信度方案。", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "Automatic Short Answer Grading with LLMs（ACM 2025）。开源权重 LLM + 评分标准提示词无需昂贵微调即可有竞争力，支撑我们" + LQ + "先不微调" + RQ + "的立场。", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "竞品参照：marking.ai。我们的差异化仍是" + LQ + "实时辅导 + 置信度 + 老师参与闭环" + RQ + "，而不只是批改。", font=SONG, size=Pt(10.5), spacing=1.5)

    add_h1(doc, "六、时间线（2.5 周出 demo）", font=HEI)
    create_table(doc,
        ["天数", "里程碑"],
        [["1-2", "建 GitHub 仓库；选定科目 + 5 道真题 + 评分标准；单次 API 调用批改 1 道题"],
         ["3-5", "三遍引擎 + 置信度逻辑；用 10 份模拟答案测试（含 2 份边界答案）"],
         ["6-8", "RAG 索引 NESA 文档；移动友好网页"],
         ["9-12", "老师复核流程；打磨；真机测试"],
         ["13 起", "找 1-2 名真实学生试用，收集反馈金句用于路演"]],
        col_widths=[2.5, 13.5])

    add_h1(doc, "七、风险与对策", font=HEI)
    create_table(doc,
        ["风险", "对策"],
        [["难题上 LLM 批改不可靠", "验证者分歧 -> 标记给老师。边界题默认人工，这是设计的一部分"],
         ["API 费用", "A 轨总计约 5 澳元；B 轨免费本地"],
         ["NESA 材料版权 / 隐私", "只用公开 HSC 材料，不存储任何真实学生数据"],
         ["没有真实教师资源", "演示用模拟教师流程 + 学生测试者的真实反馈"],
         ["团队产能（已知问题）", "每人只分一个小任务，不让任何人成为瓶颈"]],
        col_widths=[7.0, 9.0])

    add_h1(doc, "八、需要团队决策的事项", font=HEI)
    add_bullet(doc, "1. 确认科目：Enterprise Computing 还是其他 HSC 定性科目（需要有真题和评分标准可用）", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "2. 确认比赛截止日期和交付物格式（问 Alfos），以便锁定时间线", font=SONG, size=Pt(10.5), spacing=1.5)
    add_bullet(doc, "3. 分工建议：后端 + 批改引擎（1-2 人，Python）；RAG + NESA 数据收集（1 人）；前端界面（1 人）；路演 PPT + 演示脚本（1 人）；用户测试 + 反馈收集（全员，每人 1 小时）", font=SONG, size=Pt(10.5), spacing=1.5)

    doc.save("/home/gaogao/workspace/ai-coach/MVP技术选型提案_v0.1_中文版.docx")
    print("CN OK")

build_en()
build_cn()

# Copy to Desktop
desk_dir = "/mnt/c/Users/18613/Desktop/ai-coach-MVP提案"
os.makedirs(desk_dir, exist_ok=True)
for f in ["MVP_Tech_Proposal_v0.1.docx", "MVP技术选型提案_v0.1_中文版.docx"]:
    src = os.path.join("/home/gaogao/workspace/ai-coach", f)
    shutil.copy(src, os.path.join(desk_dir, f))
    print("Copied to desktop:", f)
