# -*- coding: utf-8 -*-
"""
CoachAI — Gradio 批改前端
==========================
题目选择 + 学生答案输入 + AI 批改结果展示。
视觉对齐 demo/index.html：暖白底 #FAFAF7 / 深蓝 #1F4E79 / 橙 #E69F00 / 白底圆角卡片。
支持 中 / EN 界面切换（文案存于 I18N dict）。

后端约定（尚未实现时自动给出中文友好提示，不崩溃）：
    from graphs.mark_graph import mark_answer
    result = mark_answer(question_id, student_answer) -> {
        "question_id", "status": "approved"|"flagged"|"error",
        "marks", "max_marks", "confidence_pct", "confidence_level": "high"|"medium"|"low",
        "feedback": [{"type": "good"|"improve"|"rule", "text"}],
        "flags": [], "attempts", "justification"}

启动：  python app.py   （默认 http://127.0.0.1:7860）
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import gradio as gr
from gradio.themes import Default as GradioDefault, colors as gradio_colors

# Phase 3 privacy layer: every student answer is scrubbed of PII before it
# reaches the marking engine (and its LLM calls); results are re-identified
# only locally for display.
from privacy import anonymizer

# Teacher-authored questions are merged with the official bank (same logic the
# marking engine uses, via questions_io).
from questions_io import CUSTOM_FILE, load_all_questions, save_custom_question

# Phase 5: student tracking + report comments read/write the persistence layer.
from store import db as store_db

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = BASE_DIR / "data" / "questions.json"
CUSTOM_QUESTIONS_PATH = BASE_DIR / "data" / CUSTOM_FILE
GOLDEN_PATH = BASE_DIR / "tests" / "golden_set.json"

# ---------------------------------------------------------------- i18n 文案
I18N = {
    "zh": {
        "title": "CoachAI — HSC Enterprise Computing 智能批改",
        "subtitle": "选一道题，写下你的答案，AI 按官方评分标准即时批改",
        "q_label": "选择题目",
        "q_meta": "题目",
        "q_ph": "从题库选择一道题…",
        "ans_label": "你的答案",
        "ans_ph": "在此输入 / 粘贴你的答案…",
        "ex_label": "快速示例",
        "ex_good": "加载示例答案：好答案",
        "ex_bad": "加载示例答案：差答案",
        "no_ex": "该题没有可用的{kind}示例，请手动输入答案。",
        "no_ex_good": "好",
        "no_ex_bad": "差",
        "mark_btn": "开始批改",
        "marking": "AI 正在批改…",
        "err_empty": "请先选择题目并输入答案，再开始批改。",
        "err_backend": "批改引擎尚未就绪：无法导入 graphs.mark_graph。",
        "err_backend_hint": "请先在后端实现 `mark_answer(question_id, student_answer)`（见 app.py 头部约定），或确认运行目录为项目根。",
        "err_unknown": "批改服务返回异常：",
        "res_title": "批改结果",
        "status_approved": "已批改",
        "status_flagged": "需人工复核",
        "status_error": "批改出错",
        "conf": "置信度",
        "confHigh": "高置信度",
        "confMedium": "中置信度",
        "confLow": "低置信度",
        "attempts": "答题次数",
        "fb_good": "优点",
        "fb_improve": "改进建议",
        "fb_rule": "评分标准引用",
        "fb_other": "反馈",
        "flags_head": "疑点标记",
        "just_head": "批改说明",
        "raw_label": "原始返回（JSON）",
        "marks_unit": "分",
        "q_marks_suffix": "分",
        "score_label": "建议分数 · 教师确认",
        "footer": "CoachAI · 基于 NESA 官方评分标准",
        "err_import_title": "后端批改模块未就绪",
        "add_q_label": "添加题目（自建题）",
        "add_q_note": "保存后立即出现在题目下拉框中，可直接批改。评分标准每行一条，可用「3 marks: …」标注档位。",
        "add_q_text_label": "题目题干",
        "add_q_text_ph": "在此粘贴题目原文（支持多行、中英文混排）…",
        "add_q_marks_label": "分值",
        "add_q_criteria_label": "评分标准（必填）",
        "add_q_criteria_ph": "每行一条评分标准，例如：\n3 marks: Explains ...\n2 marks: Outlines ...\n1 mark: Provides some relevant information",
        "add_q_sample_label": "参考答案（可选）",
        "add_q_sample_ph": "参考答案 / sample answer …",
        "add_q_btn": "保存题目",
        "add_q_ok": "已保存：{qid}（可在题目下拉框中选用）",
        "add_q_err": "保存失败：题干、分值和评分标准均为必填。",
        # ---- Phase 4: 教案规划 tab ----
        "tab_mark": "批改",
        "tab_lesson": "教案规划",
        "lp_year_label": "年级",
        "lp_module_label": "模块（focus area）",
        "lp_dp_label": "课程内容点（dot points）",
        "lp_dp_hint": "勾选本节课要覆盖的内容点，可多选；教案将逐条对齐。",
        "lp_dp_count": "已勾选 {n} 个内容点",
        "lp_ref_label": "参考材料（可选）",
        "lp_ref_ph": "粘贴课件、教材段落或往年材料，教案将以其术语和内容为基准…",
        "lp_dur_label": "课时长度（分钟）",
        "lp_gen_btn": "生成教案",
        "lp_empty": "勾选内容点后点击「生成教案」，结构化教案将显示在这里。",
        "lp_err_no_dp": "请至少勾选一个内容点再生成教案。",
        "lp_err_backend": "教案引擎尚未就绪：无法导入 agents.lesson_planner。",
        "lp_err_unknown": "教案生成失败：",
        "lp_r_objectives": "学习目标",
        "lp_r_flow": "课堂流程",
        "lp_r_assess": "评估点",
        "lp_r_alignment": "大纲对齐",
        "lp_draft": "草稿 · 教师修改后使用",
        "lp_min_unit": "分钟",
        "lp_meta_ref": "参考材料 {n} 字",
        "lp_meta_rag_on": "已引用 NESA TSR 材料",
        "lp_meta_rag_off": "未引用 TSR 材料",
        # ---- Phase 5: 学生 tab（追踪画像 + 报告评语） ----
        "tab_students": "学生",
        "st_student_label": "选择学生",
        "st_student_ph": "从学生名单选择…",
        "st_analyze_btn": "分析进度",
        "st_empty_profile": "选择学生后点击「分析进度」，追踪画像将显示在这里。",
        "st_sheet_sub_records": "条批改记录",
        "st_level": "当前水平",
        "st_trend": "趋势",
        "st_trend_improving": "上升",
        "st_trend_stable": "稳定",
        "st_trend_declining": "下滑",
        "st_trend_volatile": "波动",
        "st_trend_na": "数据不足",
        "st_evidence": "依据",
        "st_weak": "薄弱点",
        "st_recos": "教学建议",
        "st_no_data": "该学生暂无可用批改记录，先完成批改后再来分析。",
        "st_empty_report": "填写报告周期与补充要点，点击「生成评语」，草稿将显示在这里。",
        "st_period_label": "报告周期",
        "st_period_ph": "例如 Term 3 2026",
        "st_notes_label": "老师补充要点（可选）",
        "st_notes_ph": "写下希望评语体现的观察点，将自然融入评语…",
        "st_gen_btn": "生成评语",
        "st_comment": "评语",
        "st_comment_evidence": "评语依据",
        "st_selfeval": "学生自评提醒",
        "st_save_btn": "保存到记录",
        "st_saved": "已保存到记录：{name}（{period}）",
        "st_saved_none": "请先生成评语，再保存。",
        "st_save_err": "保存失败：",
        "st_draft": "草稿 · 教师确认后使用",
        "st_err_no_student": "请先选择学生。",
        "st_err_backend": "学生模块尚未就绪：无法导入 agents.tracker / agents.report_writer。",
        "st_err_unknown": "生成失败：",
    },
    "en": {
        "title": "CoachAI — HSC Enterprise Computing AI Marking",
        "subtitle": "Pick a question, write your answer, get instant AI feedback against official criteria",
        "q_label": "Select question",
        "q_meta": "Question",
        "q_ph": "Pick a question from the bank…",
        "ans_label": "Your answer",
        "ans_ph": "Type / paste your answer here…",
        "ex_label": "Quick examples",
        "ex_good": "Load example: strong answer",
        "ex_bad": "Load example: weak answer",
        "no_ex": "No {kind} example available for this question — please type your own answer.",
        "no_ex_good": "good",
        "no_ex_bad": "bad",
        "mark_btn": "Mark my answer",
        "marking": "AI is marking…",
        "err_empty": "Please select a question and enter an answer first.",
        "err_backend": "Marking engine not ready: cannot import graphs.mark_graph.",
        "err_backend_hint": "Implement `mark_answer(question_id, student_answer)` in the backend (contract in app.py header), or run from the project root.",
        "err_unknown": "Marking service returned an error:",
        "res_title": "Marking result",
        "status_approved": "Approved",
        "status_flagged": "Flagged for review",
        "status_error": "Marking failed",
        "conf": "Confidence",
        "confHigh": "High confidence",
        "confMedium": "Medium confidence",
        "confLow": "Low confidence",
        "attempts": "Attempts",
        "fb_good": "Strengths",
        "fb_improve": "To improve",
        "fb_rule": "Rubric reference",
        "fb_other": "Feedback",
        "flags_head": "Flags",
        "just_head": "Justification",
        "raw_label": "Raw response (JSON)",
        "marks_unit": "",
        "q_marks_suffix": "marks",
        "score_label": "Suggested mark · teacher confirmation",
        "footer": "CoachAI · aligned with NESA official marking guidelines",
        "err_import_title": "Backend marking module unavailable",
        "add_q_label": "Add your own question",
        "add_q_note": "Saved questions appear in the dropdown right away and can be marked immediately. One criterion per line; optionally prefix a band, e.g. \"3 marks: …\".",
        "add_q_text_label": "Question text",
        "add_q_text_ph": "Paste the question here (multi-line, CN/EN welcome)…",
        "add_q_marks_label": "Marks",
        "add_q_criteria_label": "Marking criteria (required)",
        "add_q_criteria_ph": "One criterion per line, e.g.\n3 marks: Explains ...\n2 marks: Outlines ...\n1 mark: Provides some relevant information",
        "add_q_sample_label": "Sample answer (optional)",
        "add_q_sample_ph": "Reference / sample answer …",
        "add_q_btn": "Save question",
        "add_q_ok": "Saved as {qid} — now selectable in the question dropdown.",
        "add_q_err": "Could not save: question text, marks and marking criteria are required.",
        # ---- Phase 4: lesson planner tab ----
        "tab_mark": "Marking",
        "tab_lesson": "Lesson planner",
        "lp_year_label": "Year",
        "lp_module_label": "Focus area (module)",
        "lp_dp_label": "Syllabus dot points",
        "lp_dp_hint": "Tick every dot point this lesson should cover (multiple allowed).",
        "lp_dp_count": "Selected: {n}",
        "lp_ref_label": "Reference material (optional)",
        "lp_ref_ph": "Paste slides, textbook extracts or past materials; the plan follows their terminology and content…",
        "lp_dur_label": "Lesson length (minutes)",
        "lp_gen_btn": "Generate lesson plan",
        "lp_empty": "Tick some dot points and click Generate. The structured lesson plan appears here.",
        "lp_err_no_dp": "Tick at least one dot point before generating.",
        "lp_err_backend": "Lesson planner engine not ready: cannot import agents.lesson_planner.",
        "lp_err_unknown": "Lesson plan generation failed:",
        "lp_r_objectives": "Learning objectives",
        "lp_r_flow": "Lesson flow",
        "lp_r_assess": "Assessment point",
        "lp_r_alignment": "Syllabus alignment",
        "lp_draft": "Draft · teacher edits before use",
        "lp_min_unit": "min",
        "lp_meta_ref": "Reference material: {n} chars",
        "lp_meta_rag_on": "NESA TSR material cited",
        "lp_meta_rag_off": "No TSR material cited",
        # ---- Phase 5: students tab (progress profile + report comment) ----
        "tab_students": "Students",
        "st_student_label": "Student",
        "st_student_ph": "Pick a student…",
        "st_analyze_btn": "Analyse progress",
        "st_empty_profile": "Pick a student and click Analyse progress. The progress profile appears here.",
        "st_sheet_sub_records": "marking records",
        "st_level": "Current level",
        "st_trend": "Trend",
        "st_trend_improving": "Improving",
        "st_trend_stable": "Stable",
        "st_trend_declining": "Declining",
        "st_trend_volatile": "Volatile",
        "st_trend_na": "Not enough data",
        "st_evidence": "Evidence",
        "st_weak": "Focus areas",
        "st_recos": "Recommendations",
        "st_no_data": "No usable marking records yet. Complete some marking first, then analyse again.",
        "st_empty_report": "Fill in the reporting period and any notes, then click Generate. The draft comment appears here.",
        "st_period_label": "Reporting period",
        "st_period_ph": "e.g. Term 3 2026",
        "st_notes_label": "Teacher notes (optional)",
        "st_notes_ph": "Observations you want reflected in the comment; they are woven in naturally…",
        "st_gen_btn": "Generate comment",
        "st_comment": "Comment",
        "st_comment_evidence": "Evidence",
        "st_selfeval": "Student self-evaluation prompt",
        "st_save_btn": "Save to records",
        "st_saved": "Saved to records: {name} ({period})",
        "st_saved_none": "Generate a comment first, then save it.",
        "st_save_err": "Could not save: ",
        "st_draft": "Draft · teacher confirms before use",
        "st_err_no_student": "Pick a student first.",
        "st_err_backend": "Student module not ready: cannot import agents.tracker / agents.report_writer.",
        "st_err_unknown": "Generation failed:",
    },
}

FB_TYPE = {
    "good": ("#2E7D32", "#E8F2E8"),
    "improve": ("#B26A00", "#FDF3E0"),
    "rule": ("#1F4E79", "#E8EEF5"),
}
CONF_COLOR = {"high": "#2E7D32", "medium": "#B26A00", "low": "#C62828"}
STATUS_STYLE = {
    "approved": ("#2E7D32", "#E8F2E8", "#2E7D32"),
    "flagged": ("#B26A00", "#FDF3E0", "#E69F00"),
    "error": ("#C62828", "#FBEAEA", "#C62828"),
}

# ---------------------------------------------------------------- 数据加载
def load_questions() -> list[dict]:
    """官方题库 + 老师自建题（custom 排在后）/ official bank + custom questions."""
    return load_all_questions([QUESTIONS_PATH, CUSTOM_QUESTIONS_PATH])


def _truncate(text: str, n: int = 78) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= n else flat[: n - 1] + "…"


def q_choices(questions: list[dict], lang: str) -> list[tuple[str, str]]:
    suffix = I18N[lang]["q_marks_suffix"]
    out = []
    for q in questions:
        label = f"{_truncate(q.get('text', q.get('id', '?')))} · ({q.get('marks', '?')} {suffix})"
        out.append((label, q.get("id")))
    return out


def _extract_examples(raw) -> dict[str, dict[str, list[str]]]:
    """把 golden_set.json（结构尽量宽容）解析成 {qid: {'good': [...], 'bad': [...]}}。"""
    examples: dict[str, dict[str, list[str]]] = {}

    def add(qid, text, quality="good"):
        target = "bad" if str(quality).lower() in ("bad", "weak", "poor", "low") else "good"
        examples.setdefault(str(qid), {}).setdefault(target, []).append(str(text))

    if isinstance(raw, dict):
        if "questions" in raw:  # {questions: [...]} 包装
            raw = raw["questions"]
        elif all(isinstance(v, (dict, list)) for v in raw.values()):
            # {qid: {'good': '...', 'bad': '...'}} / {qid: ['...', '...']} / {qid: [{answer, quality}]}
            for qid, v in raw.items():
                if isinstance(v, dict) and not any(k in v for k in ("answer", "text", "content")):
                    for key in ("good", "bad", "weak", "strong", "answer"):
                        if v.get(key):
                            quality = "good" if key in ("good", "strong") else "bad"
                            items = v[key] if isinstance(v[key], list) else [v[key]]
                            for it in items:
                                add(qid, it, quality)
                elif isinstance(v, dict):  # {qid: {answer, quality}}
                    add(qid, v.get("answer") or v.get("text") or v.get("content"),
                        v.get("quality", "good"))
                elif isinstance(v, list):
                    for it in v:
                        if isinstance(it, dict):
                            add(it.get("question_id") or it.get("qid") or it.get("id") or qid,
                                it.get("answer") or it.get("text") or it.get("content"),
                                it.get("quality", "good"))
                        else:
                            add(qid, it, "good")
            return examples
    items = raw if isinstance(raw, list) else []
    for it in items:
        if not isinstance(it, dict):
            continue
        qid = it.get("question_id") or it.get("qid") or it.get("id")
        text = it.get("answer") or it.get("text") or it.get("content")
        if not qid or text is None:
            continue
        add(qid, text, it.get("quality", "good"))
    return examples


def load_examples() -> dict[str, dict[str, list[str]]]:
    """优先 tests/golden_set.json；不存在则退回题库自带 sample_answers（作为 good 示例）。"""
    examples: dict[str, dict[str, list[str]]] = {}
    if GOLDEN_PATH.exists():
        try:
            raw = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
            examples = _extract_examples(raw)
        except Exception as e:  # noqa: BLE001
            print(f"[app] golden_set.json 解析失败: {e}", file=sys.stderr)
    if not examples:  # 退回题库内嵌 sample_answers
        for q in load_questions():
            samples = [s for s in q.get("sample_answers", []) if s]
            if samples:
                examples.setdefault(q["id"], {})["good"] = samples
    return examples


def question_text(qid: str) -> str:
    for q in load_questions():
        if q.get("id") == qid:
            return q.get("text", qid)
    return qid


def q_preview_md(qid: str, lang: str) -> str:
    """Full question text + marks, rendered above the answer box."""
    L = I18N.get(lang, I18N["en"])
    for q in load_questions():
        if q.get("id") == qid:
            marks = q.get("marks", "?")
            suffix = L["q_marks_suffix"]
            head = L.get("q_meta", "Question")
            return (f'<div class="q-meta">{head} · {marks} {suffix}</div>'
                    f'{str(q.get("text", "")).replace(chr(10), "<br>")}')
    return qid

# ---------------------------------------------------------------- 渲染
def render_result_html(res: dict, qid: str, lang: str) -> str:
    """Render mark_answer result as a designed result card (no emoji, crisp editorial style)."""
    L = I18N[lang]
    status = res.get("status", "error")
    marks = res.get("marks")
    max_marks = res.get("max_marks")
    if marks is None or max_marks is None:
        for q in load_questions():
            if q.get("id") == qid:
                if marks is None:
                    marks = 0
                if max_marks is None:
                    max_marks = q.get("marks", 0)

    conf_pct = res.get("confidence_pct")
    conf_lvl = str(res.get("confidence_level", ""))
    ring_color = {"high": "#2E7D32", "medium": "#B26A00", "low": "#C62828"}.get(conf_lvl, "#6B7684")
    ring_lvl_txt = {"high": L.get("confHigh", ""), "medium": L.get("confMedium", ""),
                    "low": L.get("confLow", "")}.get(conf_lvl, "")
    pct_safe = max(0, min(100, int(conf_pct or 0)))

    h = ['<div class="coach-result">']
    if status == "error":
        msg = res.get("message") or res.get("error") or "unknown error"
        return ('<div class="coach-error">' + msg
                + f'<div class="hint">status=error · {qid}</div></div>')

    stat_style = {"approved": ("#E8F2E8", "#2E7D32", "#1B5E20"),
                  "flagged": ("#FDF3E0", "#E69F00", "#8A5A00")}.get(status, ("#F4F6F8", "#6B7684", "#4A5568"))
    sbg, sbc, sfg = stat_style
    stat_txt = L.get(f"status_{status}", status)

    # ---- top row: big score left, ring + pills right
    unit = L["marks_unit"]
    suffix = f"/ {max_marks} {unit}".strip() if max_marks is not None else ""
    h.append('<div class="r-top">')
    h.append(f'<div class="r-score-wrap"><div class="r-score-label">{L.get("score_label", "")}</div>'
             f'<div class="r-score"><span class="big">{marks if marks is not None else "-"}</span>'
             f'<span class="max">{suffix}</span></div></div>')
    h.append('<div class="r-right">')
    if conf_pct is not None:
        h.append(f'<div class="conf-ring" style="--rc:{ring_color};--pct:{pct_safe}%">'
                 f'<div class="ring-in"><span class="pct">{pct_safe}%</span>'
                 f'<span class="lvl" style="color:{ring_color}">{ring_lvl_txt}</span></div></div>')
    attempts = res.get("attempts")
    if attempts is not None:
        h.append(f'<span class="pill">{L["attempts"]}: {attempts}</span>')
    h.append('</div></div>')

    # ---- status banner
    h.append(f'<div class="r-status" style="--sb:{sbg};--sc:{sbc};--sd:{sfg}">{stat_txt}</div>')

    # ---- feedback items
    fb = res.get("feedback") or []
    if fb:
        h.append('<div class="r-fb">')
        for item in fb:
            if isinstance(item, str):
                item = {"type": "other", "text": item}
            ftype = str(item.get("type", "other")).lower()
            fcolor, fhead = {"good": ("#2E7D32", L.get("fb_good", "Strengths")),
                             "improve": ("#B26A00", L.get("fb_improve", "To improve")),
                             "rule": ("#1F4E79", L.get("fb_rule", "Marking rule"))}.get(
                                 ftype, ("#6B7684", L.get("fb_other", "Feedback")))
            h.append('<div class="fb-item">'
                     f'<div class="bar" style="background:{fcolor}"></div>'
                     '<div class="fb-body">'
                     f'<div class="fb-head" style="color:{fcolor}">{fhead}</div>'
                     f'<div class="fb-text">{item.get("text", "")}</div>'
                     '</div></div>')
        h.append('</div>')

    # ---- flags
    flags = res.get("flags") or []
    if flags:
        h.append(f'<div class="r-flags"><b>{L["flags_head"]}</b><ul style="margin:6px 0 0 18px">'
                 + "".join(f"<li>{f}</li>" for f in flags) + "</ul></div>")

    # ---- justification
    just = res.get("justification")
    if just:
        h.append(f'<div class="r-just"><b>{L["just_head"]}</b><br>{just}</div>')

    h.append("</div>")
    return "".join(h)
def err_card(title: str, hint: str = "") -> str:
    html_ = f'<div class="coach-error">{title}'
    if hint:
        html_ += f'<div class="hint">{hint}</div>'
    return html_ + "</div>"

# ---------------------------------------------------------------- 教案规划（Phase 4）
def lp_modules(year: str) -> list:
    """Focus-area names for a year, straight from data/syllabus.json ([] on failure)."""
    try:
        from agents.lesson_planner import list_modules, load_syllabus  # noqa: PLC0415
        return list_modules(load_syllabus(), year)
    except Exception as e:  # noqa: BLE001
        print(f"[app] syllabus 加载失败: {e}", file=sys.stderr)
        return []


def lp_dot_point_choices(year: str, focus_area: str) -> list:
    """(label, value) pairs for the checkbox group; value = dot point text."""
    try:
        from agents.lesson_planner import load_syllabus, module_dot_points  # noqa: PLC0415
        return [(d["text"], d["text"]) for d in module_dot_points(load_syllabus(), year, focus_area)]
    except Exception as e:  # noqa: BLE001
        print(f"[app] dot points 加载失败: {e}", file=sys.stderr)
        return []


def lp_selection_note(dot_points, lang: str) -> str:
    """Tiny live counter under the checkbox group."""
    L = I18N.get(lang, I18N["en"])
    return L["lp_dp_count"].format(n=len(dot_points or []))


def render_plan_empty(lang: str) -> str:
    """Placeholder shown before the first generation."""
    return f'<div class="plan-empty">{I18N.get(lang, I18N["en"])["lp_empty"]}</div>'


def render_plan_html(plan: dict, lang: str) -> str:
    """Render a lesson plan dict as a paper-sheet style HTML block.

    Plain editorial layout: title + rule, objectives list, flow rows with a
    time column, assessment strip and the syllabus alignment list. No emoji.
    """
    L = I18N.get(lang, I18N["en"])
    esc = html.escape

    h = ['<div class="plan-sheet">']
    # ---- head: title + year / module / duration / draft note
    h.append('<div class="plan-head">')
    h.append(f'<div class="plan-title">{esc(str(plan.get("title", "")).strip())}</div>')
    sub_bits = [esc(str(plan.get("year", "")).strip()),
                esc(str(plan.get("focus_area", "")).strip())]
    sub_bits = [b for b in sub_bits if b]
    duration = plan.get("duration_min")
    if duration:
        sub_bits.append(f'{esc(str(duration))} {L["lp_min_unit"]}')
    sub_bits.append(L["lp_draft"])
    h.append(f'<div class="plan-sub">{" · ".join(sub_bits)}</div>')
    h.append('</div>')

    # ---- objectives
    objectives = [str(o).strip() for o in (plan.get("objectives") or []) if str(o).strip()]
    if objectives:
        h.append(f'<h4 class="plan-h">{L["lp_r_objectives"]}</h4><ul class="plan-objectives">')
        h += [f"<li>{esc(o)}</li>" for o in objectives]
        h.append('</ul>')

    # ---- flow rows
    flow = plan.get("flow") or []
    if flow:
        h.append(f'<h4 class="plan-h">{L["lp_r_flow"]}</h4><div class="flow">')
        for seg in flow:
            if not isinstance(seg, dict):
                continue
            t = esc(str(seg.get("time", "")).strip())
            a = esc(str(seg.get("activity", "")).strip())
            d = esc(str(seg.get("detail", "")).strip())
            detail = f'<div class="d">{d}</div>' if d else ""
            h.append('<div class="flow-row">'
                     f'<div class="flow-time">{t}</div>'
                     f'<div class="flow-body"><div class="t">{a}</div>{detail}</div>'
                     '</div>')
        h.append('</div>')

    # ---- assessment strip
    assess = str(plan.get("assessment", "")).strip()
    if assess:
        text = "" if assess.startswith("(") else esc(assess)
        h.append(f'<div class="assess"><b>{L["lp_r_assess"]}</b>{text}</div>')

    # ---- alignment (the ticked dot points)
    alignment = [str(d).strip() for d in (plan.get("alignment") or []) if str(d).strip()]
    if alignment:
        h.append(f'<h4 class="plan-h">{L["lp_r_alignment"]}</h4><div class="aligned">')
        h += [f'<div class="dp">{esc(d)}</div>' for d in alignment]
        h.append('</div>')

    # ---- provenance footer
    gen = plan.get("generated_with") or {}
    meta = [L["lp_meta_ref"].format(n=int(gen.get("reference_len") or 0)),
            L["lp_meta_rag_on"] if gen.get("rag_used") else L["lp_meta_rag_off"]]
    h.append(f'<div class="plan-meta">{" · ".join(meta)}</div>')

    h.append('</div>')
    return "".join(h)

# ---------------------------------------------------------------- 业务逻辑
def mark_answer_safe(qid: str, answer: str, lang: str):
    """调用后端；import 失败 / status=error / 其他异常 → 返回友好错误卡片。"""
    L = I18N[lang]
    if not qid:
        return err_card(L["err_empty"]), None
    if not (answer or "").strip():
        return err_card(L["err_empty"]), None
    try:
        from graphs.mark_graph import mark_answer as _mark  # noqa: PLC0415
    except Exception as e:  # noqa: BLE001
        print(f"[app] import graphs.mark_graph 失败: {e}", file=sys.stderr)
        return err_card(L["err_backend"], L["err_backend_hint"]), {"error": str(e)}

    # ---- Phase 3 privacy layer: anonymise BEFORE the engine (and its LLM
    # calls) ever see the answer, then restore real values for local display.
    # Trade-off (deliberate): if anonymisation breaks we DEGRADE to marking the
    # raw text instead of BLOCKING the marking — demo availability wins here;
    # the stderr warning below is the audit trail for that decision.
    safe_answer, mapping = answer, {}
    try:
        safe_answer, mapping = anonymizer.anonymize(answer)
    except Exception as e:  # noqa: BLE001 — privacy failure must never block marking
        print(f"[app] anonymisation failed, degrading to raw-text marking (privacy warning): {e}",
              file=sys.stderr)

    try:
        res = _mark(qid, safe_answer)
    except Exception as e:  # noqa: BLE001
        print(f"[app] mark_answer 调用失败: {e}", file=sys.stderr)
        return err_card(f'{L["err_unknown"]} {e}'), {"error": str(e)}
    if not isinstance(res, dict):
        return err_card(f'{L["err_unknown"]} unexpected type {type(res).__name__}'), {"raw": res}

    # Re-identify placeholders in the result for the local report only
    # (restored text is never sent back to any LLM).
    try:
        res = anonymizer.restore_result(res, mapping)
    except Exception as e:  # noqa: BLE001
        print(f"[app] result re-identification failed (placeholders kept): {e}", file=sys.stderr)
    # Non-intrusive diagnostics flag; render_result_html only reads known fields.
    res["_privacy"] = {"anonymised": bool(mapping), "items": len(mapping)}

    if res.get("status") == "error":
        msg = res.get("message") or res.get("error") or "unknown error"
        return err_card(f'{L["status_error"]} — {msg}'), res
    return render_result_html(res, qid, lang), res

# ---------------------------------------------------------------- 教案业务逻辑
def generate_plan_safe(dot_points, reference_text, year, duration_min, focus_area, ui_lang):
    """Generate one lesson plan; engine/LLM failures come back as friendly cards."""
    L = I18N.get(ui_lang, I18N["en"])
    dots = [str(d).strip() for d in (dot_points or []) if str(d).strip()]
    if not dots:
        return err_card(L["lp_err_no_dp"])
    try:
        from agents.lesson_planner import generate_lesson_plan, infer_lang  # noqa: PLC0415
    except Exception as e:  # noqa: BLE001
        print(f"[app] import agents.lesson_planner 失败: {e}", file=sys.stderr)
        return err_card(L["lp_err_backend"], str(e))

    # The plan's language follows the reference material / dot points, not the
    # UI chrome language (Chinese material in -> Chinese plan out).
    plan_lang = infer_lang(reference_text or "", " ".join(dots))
    try:
        plan = generate_lesson_plan(
            dots, reference_text=reference_text or "", year=year,
            duration_min=int(duration_min or 60), focus_area=focus_area or "",
            lang=plan_lang,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[app] generate_lesson_plan 调用失败: {e}", file=sys.stderr)
        return err_card(f'{L["lp_err_unknown"]} {e}')
    return render_plan_html(plan, plan_lang)

# ---------------------------------------------------------------- 学生追踪（Phase 5）
# Trend tag colours: improving / stable / declining / volatile / not enough data.
ST_TREND_COLOR = {
    "improving": "#2F6D4F",
    "stable": "#1F4E79",
    "declining": "#B03A2E",
    "volatile": "#B26A00",
    "insufficient_data": "#8A93A0",
}


def st_student_choices(students: list, lang: str) -> list[tuple[str, int]]:
    """(label, value=student id) pairs, e.g. 'Alex Chen · Year 12'."""
    out = []
    for s in students or []:
        label = str(s.get("name") or "?").strip()
        year = str(s.get("year") or "").strip()
        if year:
            label = f"{label} · {year}"
        out.append((label, s.get("id")))
    return out


def render_profile_empty(lang: str) -> str:
    return f'<div class="plan-empty">{I18N.get(lang, I18N["en"])["st_empty_profile"]}</div>'


def render_report_empty(lang: str) -> str:
    return f'<div class="plan-empty">{I18N.get(lang, I18N["en"])["st_empty_report"]}</div>'


def st_trend_label(trend: str, L: dict) -> str:
    key = "st_trend_na" if trend in ("", "insufficient_data") else f"st_trend_{trend}"
    return L.get(key, L.get("st_trend_na", trend))


def render_profile_html(profile: dict, lang: str) -> str:
    """Render a tracker profile as a paper-sheet card (no emoji, no markdown)."""
    L = I18N.get(lang, I18N["en"])
    esc = html.escape

    h = ['<div class="st-sheet">']
    h.append('<div class="st-head">')
    h.append(f'<div class="st-name">{esc(str(profile.get("student_name", "")).strip())}</div>')
    sub_bits = [f'{int(profile.get("total_submissions") or 0)} {L["st_sheet_sub_records"]}']
    if profile.get("avg_score_rate") is not None:
        sub_bits.append(f'{L["st_level"]}: {round(float(profile["avg_score_rate"]) * 100)}%')
    h.append(f'<div class="st-sub">{" · ".join(sub_bits)}</div>')
    h.append('</div>')

    if not profile.get("has_data"):
        h.append(f'<div class="st-note">{esc(L["st_no_data"])}</div>')
        h.append('</div>')
        return "".join(h)

    # ---- current level (LLM-written prose)
    level = str(profile.get("current_level") or "").strip()
    if level:
        h.append(f'<div class="st-row"><div class="st-k">{L["st_level"]}</div>'
                 f'<div class="st-v">{esc(level)}</div></div>')

    # ---- trend tag + deterministic evidence bullets
    trend = str(profile.get("trend") or "")
    color = ST_TREND_COLOR.get(trend, ST_TREND_COLOR["insufficient_data"])
    h.append(f'<div class="st-row"><div class="st-k">{L["st_trend"]}</div>'
             f'<div class="st-v"><span class="st-tag" style="color:{color}">'
             f'{esc(st_trend_label(trend, L))}</span>')
    evidence = [str(e).strip() for e in (profile.get("trend_evidence") or []) if str(e).strip()]
    if evidence:
        h.append(f'<div class="st-k" style="margin-top:12px">{L["st_evidence"]}</div><ul class="st-list">')
        h += [f"<li>{esc(e)}</li>" for e in evidence]
        h.append('</ul>')
    h.append('</div></div>')

    # ---- weak areas (deterministic)
    weak = [str(w).strip() for w in (profile.get("weak_areas") or []) if str(w).strip()]
    if weak:
        h.append(f'<div class="st-row"><div class="st-k">{L["st_weak"]}</div><ul class="st-list">')
        h += [f"<li>{esc(w)}</li>" for w in weak]
        h.append('</ul></div>')

    # ---- recommendations (LLM-written)
    recos = [str(r).strip() for r in (profile.get("recommendations") or []) if str(r).strip()]
    if recos:
        h.append(f'<div class="st-row"><div class="st-k">{L["st_recos"]}</div><ul class="st-list">')
        h += [f"<li>{esc(r)}</li>" for r in recos]
        h.append('</ul></div>')

    h.append('</div>')
    return "".join(h)


def render_report_html(report: dict, lang: str) -> str:
    """Render a generated report comment as a paper-sheet card."""
    L = I18N.get(lang, I18N["en"])
    esc = html.escape

    h = ['<div class="st-sheet">']
    h.append('<div class="st-head">')
    h.append(f'<div class="st-name">{esc(str(report.get("student_name", "")).strip())}</div>')
    sub_bits = [esc(str(report.get("period") or "").strip() or "-"), L["st_draft"]]
    h.append(f'<div class="st-sub">{" · ".join(sub_bits)}</div>')
    h.append('</div>')

    h.append(f'<div class="st-comment-text">{esc(str(report.get("comment") or "").strip())}</div>')

    evidence = [str(e).strip() for e in (report.get("evidence") or []) if str(e).strip()]
    if evidence:
        h.append(f'<div class="st-k" style="margin-top:22px">{L["st_comment_evidence"]}</div>'
                 '<ul class="st-list">')
        h += [f"<li>{esc(e)}</li>" for e in evidence]
        h.append('</ul>')

    self_eval = str(report.get("self_eval_note") or "").strip()
    if self_eval:
        h.append(f'<div class="st-self"><b>{L["st_selfeval"]}</b>{esc(self_eval)}</div>')

    h.append('</div>')
    return "".join(h)


def st_analyze_safe(student_id, lang: str) -> str:
    """Run the tracker; import/LLM failures come back as friendly cards."""
    L = I18N.get(lang, I18N["en"])
    if not student_id:
        return err_card(L["st_err_no_student"])
    try:
        from agents.tracker import analyze_student  # noqa: PLC0415
    except Exception as e:  # noqa: BLE001
        print(f"[app] import agents.tracker 失败: {e}", file=sys.stderr)
        return err_card(L["st_err_backend"], str(e))
    try:
        profile = analyze_student(int(student_id))
    except Exception as e:  # noqa: BLE001
        print(f"[app] analyze_student 调用失败: {e}", file=sys.stderr)
        return err_card(f'{L["st_err_unknown"]} {e}')
    if not isinstance(profile, dict):
        return err_card(f'{L["st_err_unknown"]} unexpected type {type(profile).__name__}')
    return render_profile_html(profile, lang)


def st_generate_safe(student_id, period, teacher_notes, lang: str):
    """Generate one report comment. Returns (html, report_state, save_btn_update)."""
    L = I18N.get(lang, I18N["en"])
    off = gr.update(interactive=False)
    if not student_id:
        return err_card(L["st_err_no_student"]), None, off
    try:
        from agents.report_writer import generate_report_comment  # noqa: PLC0415
    except Exception as e:  # noqa: BLE001
        print(f"[app] import agents.report_writer 失败: {e}", file=sys.stderr)
        return err_card(L["st_err_backend"], str(e)), None, off
    try:
        report = generate_report_comment(
            int(student_id), (period or "").strip(),
            teacher_notes=(teacher_notes or "").strip(),
        )
    except Exception as e:  # noqa: BLE001
        print(f"[app] generate_report_comment 调用失败: {e}", file=sys.stderr)
        return err_card(f'{L["st_err_unknown"]} {e}'), None, off
    if not isinstance(report, dict) or not report.get("comment"):
        return err_card(f'{L["st_err_unknown"]} empty comment'), None, off
    return render_report_html(report, lang), report, gr.update(interactive=True)


def st_save_safe(report, lang: str):
    """Persist the generated comment to store.db. Returns (status_md, save_btn)."""
    L = I18N.get(lang, I18N["en"])
    if not report:
        return L["st_saved_none"], gr.update()
    try:
        store_db.add_report_comment(
            int(report.get("student_id")), report.get("period"),
            report.get("comment"), teacher_notes=report.get("teacher_notes"),
        )
    except Exception as e:  # noqa: BLE001
        print(f"[app] add_report_comment 调用失败: {e}", file=sys.stderr)
        return f'{L["st_save_err"]} {e}', gr.update()
    return (L["st_saved"].format(name=report.get("student_name", ""),
                                 period=report.get("period") or "-"),
            gr.update(interactive=False))

# ---------------------------------------------------------------- Gradio 界面
PAGE_CSS = """
:root { --paper:#FAFAF7; --ink:#1A2332; --blue:#1F4E79; --blue-hover:#143A5C;
        --orange:#E69F00; --orange-deep:#C77F00; --line:#E8E2D8; --card:#FFFFFF;
        --red:#B03A2E; --rule:#E2DED4;
        --soft:#F5F2EC; --serif: Georgia, "Times New Roman", "Songti SC", "SimSun", serif; }
body { background: var(--paper) !important; }
body, .gradio-container { color: var(--ink); }
.gradio-container { max-width: 1120px !important; margin: 0 auto !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Microsoft YaHei", sans-serif !important;
    padding-bottom: 60px !important; }

/* ---------- header ---------- */
#coach-header { position: relative; background: var(--card); border:1px solid var(--line);
    border-radius: 10px; box-shadow: 0 1px 2px rgba(26,35,50,.03), 0 12px 32px rgba(26,35,50,.05);
    padding: 30px 34px 26px; margin-top: 26px; overflow: hidden; }
#coach-header::before { content:""; position:absolute; top:0; left:0; right:0; height:3px;
    background: linear-gradient(90deg, var(--blue) 0%, var(--blue) 62%, var(--orange) 62%, var(--orange) 100%); }
#coach-header .logo { display:flex; align-items:center; gap:12px; }
#coach-header .logo .mark { background: linear-gradient(135deg, #245A8C, var(--blue)); color:#fff;
    border-radius:8px; width:42px; height:42px; display:inline-flex; align-items:center;
    justify-content:center; font-size:.82em; font-weight:800; letter-spacing:1px;
    box-shadow: 0 4px 12px rgba(31,78,121,.25); }
#coach-header .logo .brandname { font-family: var(--serif); font-weight:700; font-size:1.5em;
    letter-spacing:.2px; color: var(--ink); }
#coach-header .logo .hsc-tag { color: var(--orange-deep); font-size:.68em; font-weight:700;
    border:1.5px solid var(--orange); border-radius:4px; padding:2px 8px; letter-spacing:.6px;
    margin-left:2px; }
#coach-header .sub { color:#6B7684; font-size:.94em; margin-top:7px; line-height:1.5; }

/* ---------- language segmented control ---------- */
#lang-switch { background: var(--soft); border-radius:8px; padding:3px; display:inline-block; }
#lang-switch button { border-radius: 6px !important; font-weight:600 !important;
    border: none !important; font-size:.88em !important; padding: 6px 16px !important; }
#lang-switch .selected { background: var(--blue) !important; color:#fff !important;
    box-shadow: 0 2px 6px rgba(31,78,121,.3) !important; }
#lang-switch button:not(.selected) { background: transparent !important; color:#5A6472 !important; }

/* ---------- panels ---------- */
.panel { background: var(--card); border:1px solid var(--line); border-radius:10px;
    box-shadow: 0 1px 2px rgba(26,35,50,.03), 0 8px 24px rgba(26,35,50,.04);
    padding: 26px 30px; margin: 4px 0 20px; }
.panel label, .panel .label-wrap span { text-transform: uppercase; font-size: 11px !important;
    font-weight: 700 !important; letter-spacing: 1.2px !important; color:#7A8494 !important; }
.panel textarea, .panel input { border:1px solid #DCD5C9 !important; border-radius:6px !important;
    background:#FDFCFA !important; font-size: .98em !important; }
.panel textarea:focus, .panel input:focus { border-color: var(--blue) !important;
    box-shadow: 0 0 0 3px rgba(31,78,121,.12) !important; }

/* ---------- question preview ---------- */
#q-preview { background: var(--soft); border:1px solid var(--line); border-radius:8px;
    padding:18px 22px; line-height:1.7; font-size:.97em; color:#33404F; margin-top:4px; }
#q-preview .q-meta { color: var(--blue); font-size:.75em; font-weight:800; letter-spacing:1.4px;
    text-transform: uppercase; margin-bottom:8px; }
#q-preview table, #q-preview td, #q-preview th { border: 1px solid #E0DACD; border-collapse: collapse;
    padding: 4px 10px; font-size:.92em; background:#fff; }
#q-preview td { font-family: Consolas, Menlo, monospace; }

/* ---------- buttons ---------- */
#mark-btn, #lp-gen-btn { background: linear-gradient(180deg, #245A8C, var(--blue)) !important;
    border: none !important; border-radius: 8px !important; font-weight: 700 !important;
    padding: 15px 56px !important; font-size: 1.05em !important; letter-spacing: .3px;
    box-shadow: 0 4px 14px rgba(31,78,121,.28) !important; transition: all .18s ease !important; }
#mark-btn:hover, #lp-gen-btn:hover { transform: translateY(-1px); box-shadow: 0 8px 22px rgba(31,78,121,.35) !important; }
#mark-btn:active, #lp-gen-btn:active { transform: translateY(0); box-shadow: 0 2px 8px rgba(31,78,121,.25) !important; }
#mark-btn:disabled, #lp-gen-btn:disabled { opacity:.55 !important; }

/* ---------- example radio ---------- */
#ex-radio { display:flex; gap:10px; }
#ex-radio label { background:#FDFCFA; border:1px solid #DCD5C9; border-radius:6px;
    padding: 8px 18px !important; cursor:pointer; font-weight:600; font-size:.9em !important;
    text-transform:none !important; letter-spacing:0 !important; }
#ex-radio label:has(input:checked) { border-color: var(--blue); color: var(--blue);
    background: #F0F4F9; }

/* ---------- result card ---------- */
.coach-result { background:#fff; border:1px solid var(--line); border-radius:12px;
    padding: 30px 32px; box-shadow: 0 1px 2px rgba(26,35,50,.03), 0 16px 40px rgba(26,35,50,.06);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }
.coach-result .r-top { display:flex; align-items:center; justify-content:space-between; gap:20px; flex-wrap:wrap; }
.coach-result .r-score { display:flex; align-items:baseline; gap:4px; }
.coach-result .r-score-wrap { display:flex; flex-direction:column; gap:7px; }
.coach-result .r-score-label { font-size:.7em; font-weight:800; letter-spacing:1.3px;
    text-transform:uppercase; color:#8A93A0; }
.coach-result .r-score .big { font-size:3.4em; font-weight:800; color:var(--blue); line-height:1; letter-spacing:-1px; }
.coach-result .r-score .max { font-size:1.1em; color:#8A93A0; font-weight:600; }
.coach-result .r-right { display:flex; align-items:center; gap:18px; flex-wrap:wrap; }
.coach-result .conf-ring { width:92px; height:92px; border-radius:50%; display:grid; place-items:center;
    background: conic-gradient(var(--rc,#2E7D32) var(--pct,70)%, #EFEBE3 0); }
.coach-result .conf-ring .ring-in { width:70px; height:70px; border-radius:50%; background:#fff;
    display:flex; flex-direction:column; align-items:center; justify-content:center; }
.coach-result .conf-ring .ring-in .pct { font-size:1.35em; font-weight:800; color:var(--ink); line-height:1; }
.coach-result .conf-ring .ring-in .lvl { font-size:.6em; font-weight:700; color:var(--rc,#2E7D32); margin-top:2px;
    text-transform:uppercase; letter-spacing:.5px; }
.coach-result .pill { border:1px solid #D8D2C6; color:#5A6472; border-radius:6px; padding:5px 12px;
    font-size:.78em; font-weight:700; }
.coach-result .r-status { margin-top:18px; display:flex; align-items:center; gap:10px;
    background: var(--sb,#E8F2E8); border-left:4px solid var(--sc,#2E7D32); color: var(--sd,#1B5E20);
    border-radius:6px; padding:11px 16px; font-weight:700; font-size:.95em; }
.coach-result .r-fb { margin-top:22px; }
.coach-result .fb-item { display:flex; gap:14px; margin-top:12px; }
.coach-result .fb-item .bar { width:4px; border-radius:2px; flex-shrink:0; }
.coach-result .fb-item .fb-body { flex:1; background:#FBF9F5; border:1px solid #EFEAE0; border-radius:8px;
    padding:12px 16px; }
.coach-result .fb-item .fb-head { font-size:.72em; font-weight:800; letter-spacing:1.2px;
    text-transform:uppercase; margin-bottom:4px; }
.coach-result .fb-item .fb-text { font-size:.94em; line-height:1.6; color:#33404F; }
.coach-result .r-flags { margin-top:16px; background:#FBEAEA; border:1px solid #EEC7C7; border-left:4px solid #C62828;
    border-radius:6px; padding:12px 16px; font-size:.9em; color:#8B1A1A; }
.coach-result .r-just { margin-top:20px; color:#6B7684; font-size:.85em; line-height:1.6;
    border-top:1px dashed #E3DCD0; padding-top:14px; }
.coach-result .r-just b { color: var(--blue); }
.coach-error { background:#FBEAEA; border:1px solid #EEC7C7; border-left:4px solid #C62828;
    border-radius:8px; padding:16px 20px; font-weight:700; color:#8B1A1A; }
.coach-error .hint { font-weight:400; color:#A05656; font-size:.88em; margin-top:6px; }

/* ---------- lesson plan sheet (Phase 4) ---------- */
#lp-result .plan-sheet { background:#fff; border:1px solid #C9C4B8; border-radius:12px;
    padding: 30px 32px 24px; box-shadow: 0 1px 2px rgba(26,35,50,.03), 0 16px 40px rgba(26,35,50,.06); }
#lp-result .plan-head { border-bottom: 2px solid var(--ink); padding-bottom: 12px; }
#lp-result .plan-title { font-size: 1.35em; font-weight: 800; color: var(--ink); letter-spacing: -.01em; }
#lp-result .plan-sub { font-size: .82em; color:#6B7684; margin-top: 5px; }
#lp-result .plan-h { font-size:.72em; font-weight:800; letter-spacing:1.2px; text-transform:uppercase;
    color:#7A8494; margin: 24px 0 10px; }
#lp-result ul.plan-objectives { list-style:none; margin:0; padding:0; }
#lp-result ul.plan-objectives li { padding: 6px 0 6px 20px; position: relative; font-size: .95em;
    color:#33404F; border-bottom: 1px solid #F0EDE5; }
#lp-result ul.plan-objectives li::before { content:""; position:absolute; left:2px; top:14px;
    width:5px; height:5px; border-radius:50%; background: var(--orange); }
#lp-result .flow { border-top: 1px solid #E2DED4; }
#lp-result .flow-row { display:grid; grid-template-columns: 92px 1fr; border-bottom: 1px solid #E2DED4; }
#lp-result .flow-time { padding: 11px 12px 11px 0; font-size:.8em; font-weight:700; color: var(--blue);
    border-right: 1px solid #E2DED4; }
#lp-result .flow-body { padding: 11px 0 11px 16px; }
#lp-result .flow-body .t { font-size:.95em; font-weight:600; color: var(--ink); }
#lp-result .flow-body .d { font-size:.86em; color:#6B7684; margin-top: 3px; line-height:1.55; }
#lp-result .assess { margin-top: 20px; padding: 12px 16px; background:#F0F4EF;
    border-left: 3px solid #2F5D3A; font-size:.88em; color:#24422C; line-height:1.6; }
#lp-result .assess b { display:block; font-size:.72em; letter-spacing:1.1px;
    text-transform: uppercase; margin-bottom: 3px; color:#2F5D3A; }
#lp-result .aligned { font-size:.84em; color:#4A5568; }
#lp-result .aligned .dp { padding: 3px 0 3px 14px; position: relative; line-height:1.55; }
#lp-result .aligned .dp::before { content:""; position:absolute; left:2px; top:12px;
    width:4px; height:4px; border-radius:50%; background: var(--orange); }
#lp-result .plan-meta { margin-top: 22px; padding-top: 12px; border-top: 1px dashed #E3DCD0;
    font-size:.76em; color:#8A93A0; letter-spacing:.2px; }
.plan-empty { background:#FBF9F5; border:1px dashed #DCD5C9; border-radius:10px;
    padding: 26px 24px; color:#8A93A0; font-size:.92em; text-align:center; }
#lp-dots { max-height: 420px; overflow-y: auto; }
#lp-dots label { text-transform:none !important; letter-spacing:0 !important; font-weight:500 !important;
    font-size:.92em !important; color:#33404F !important; line-height:1.5; }
#lp-counter p { font-size:.82em !important; color:#8A93A0 !important; margin: 2px 0 0; }

/* ---------- students tab (Phase 5) ---------- */
#st-analyze-btn, #st-gen-btn { background: linear-gradient(180deg, #245A8C, var(--blue)) !important;
    border: none !important; border-radius: 8px !important; font-weight: 700 !important;
    padding: 15px 56px !important; font-size: 1.05em !important; letter-spacing: .3px;
    box-shadow: 0 4px 14px rgba(31,78,121,.28) !important; transition: all .18s ease !important; }
#st-analyze-btn:hover, #st-gen-btn:hover { transform: translateY(-1px);
    box-shadow: 0 8px 22px rgba(31,78,121,.35) !important; }
#st-analyze-btn:active, #st-gen-btn:active { transform: translateY(0); }
#st-analyze-btn:disabled, #st-gen-btn:disabled { opacity:.55 !important; }
#st-save-btn { border:1px solid var(--blue) !important; color: var(--blue) !important;
    background:#fff !important; border-radius:8px !important; font-weight:700 !important;
    padding: 11px 30px !important; transition: all .18s ease !important; }
#st-save-btn:hover { background:#F0F4F9 !important; }
#st-save-btn:disabled { opacity:.5 !important; }
#st-status p { font-size:.88em !important; color:#2F6D4F !important; margin: 4px 0 0; }
#st-sheet, .st-sheet { background:#fff; border:1px solid var(--rule); border-radius:12px;
    padding: 28px 32px 24px; box-shadow: 0 1px 2px rgba(26,35,50,.03), 0 14px 36px rgba(26,35,50,.05); }
.st-sheet .st-head { border-bottom: 2px solid var(--ink); padding-bottom: 12px; margin-bottom: 18px; }
.st-sheet .st-name { font-size: 1.3em; font-weight: 800; color: var(--ink); letter-spacing: -.01em; }
.st-sheet .st-sub { font-size: .8em; color:#7A8494; margin-top: 5px; }
.st-sheet .st-k { font-size:.7em; font-weight:800; letter-spacing:1.2px; text-transform:uppercase;
    color:#7A8494; margin-bottom:6px; }
.st-sheet .st-row { margin-bottom: 18px; }
.st-sheet .st-v { font-size:.95em; color:#33404F; line-height:1.7; }
.st-sheet .st-tag { display:inline-block; border-radius:5px; padding:3px 11px; font-size:.78em;
    font-weight:700; border:1px solid currentColor; }
.st-sheet .st-list { margin: 6px 0 0 18px; padding:0; }
.st-sheet .st-list li { padding: 3px 0; font-size:.92em; color:#33404F; line-height:1.6; }
.st-sheet .st-note { margin-top:4px; color:#8A93A0; font-size:.92em; }
.st-sheet .st-self { margin-top:20px; padding:12px 16px; background: var(--soft);
    border-left:3px solid var(--rule); border-radius:0 6px 6px 0; font-size:.87em; color:#5A6472; }
.st-sheet .st-self b { display:block; color: var(--ink); font-size:.72em; letter-spacing:1.1px;
    text-transform:uppercase; margin-bottom:4px; }
.st-sheet .st-comment-text { font-size:1em; line-height:1.8; color: var(--ink); }
.st-sheet .st-comment-text + .st-k { margin-top:22px; }

@media (max-width: 760px) {
    .gradio-container { padding: 0 4px 40px !important; }
    #coach-header { padding: 22px 20px 18px; }
    .panel { padding: 18px 16px; }
    .coach-result { padding: 20px 16px; }
    .coach-result .r-score .big { font-size: 2.6em; }
    .conf-ring { width: 76px; height: 76px; }
    .conf-ring .ring-in { width: 58px; height: 58px; }
}
"""

def build_ui() -> gr.Blocks:
    questions = load_questions()
    with gr.Blocks(title="CoachAI") as demo:
        lang_state = gr.State("zh")
        qid_state = gr.State(questions[0]["id"] if questions else None)
        # Phase 5: the last generated report comment, held for "save to records".
        st_last_report = gr.State(None)

        # ---------- 顶部：品牌 + 语言切换 ----------
        with gr.Row(elem_id="coach-header"):
            with gr.Column(scale=4):
                title_md = gr.Markdown(
                    f'<div class="logo"><span class="mark">AI</span><span class="brandname">CoachAI</span> '
                    f'<span style="color:#E69F00;font-size:.62em;font-weight:700;border:1.5px solid #E69F00;'
                    f'border-radius:4px;padding:2px 8px;vertical-align:middle">HSC</span></div>'
                    f'<div class="sub">{I18N["zh"]["subtitle"]}</div>')
            with gr.Column(scale=1, elem_id="lang-switch"):
                lang_radio = gr.Radio(["中文", "EN"], value="中文", show_label=False,
                                      interactive=True, elem_id="lang-select")

        # ================= 标签页：批改 / 教案规划 =================
        with gr.Tabs(elem_id="coach-tabs"):
            # -------------------------------------------------- Tab 1: 批改
            with gr.Tab(I18N["zh"]["tab_mark"], id="tab-mark") as tab_mark:
                # ---------- 1. 选题 ----------
                with gr.Group(elem_classes="panel"):
                    q_dropdown = gr.Dropdown(choices=q_choices(questions, "zh"), value=questions[0]["id"] if questions else None,
                                             label=I18N["zh"]["q_label"], elem_id="q-drop")
                    q_preview = gr.Markdown(q_preview_md(questions[0]["id"], "zh") if questions else "", elem_id="q-preview")

                # ---------- 2. 答案 ----------
                with gr.Group(elem_classes="panel"):
                    ans_box = gr.Textbox(label=I18N["zh"]["ans_label"], lines=7, placeholder=I18N["zh"]["ans_ph"],
                                         elem_id="ans-box")
                    ex_radio = gr.Radio([I18N["zh"]["ex_good"], I18N["zh"]["ex_bad"]], label=I18N["zh"]["ex_label"],
                                        value=None, elem_id="ex-radio")

                # ---------- 3. 批改 ----------
                mark_btn = gr.Button(I18N["zh"]["mark_btn"], variant="primary", elem_id="mark-btn", size="lg")
                result_md = gr.Markdown()
                raw_accord = gr.Accordion(I18N["zh"]["raw_label"], open=False, elem_classes="panel")
                with raw_accord:
                    raw_json = gr.JSON(value=None, show_label=False)

                # ---------- 4. 自建题目（老师录入，默认收起） ----------
                with gr.Accordion(I18N["zh"]["add_q_label"], open=False,
                                  elem_classes="panel", elem_id="add-q") as add_accord:
                    cq_note = gr.Markdown(I18N["zh"]["add_q_note"], elem_id="add-q-note")
                    cq_text = gr.Textbox(label=I18N["zh"]["add_q_text_label"], lines=6,
                                         placeholder=I18N["zh"]["add_q_text_ph"])
                    cq_marks = gr.Number(label=I18N["zh"]["add_q_marks_label"], value=None,
                                         precision=0, minimum=1, maximum=100)
                    cq_criteria = gr.Textbox(label=I18N["zh"]["add_q_criteria_label"], lines=5,
                                             placeholder=I18N["zh"]["add_q_criteria_ph"])
                    cq_sample = gr.Textbox(label=I18N["zh"]["add_q_sample_label"], lines=3,
                                           placeholder=I18N["zh"]["add_q_sample_ph"])
                    cq_save = gr.Button(I18N["zh"]["add_q_btn"], elem_id="add-q-btn")
                    cq_status = gr.Markdown("", elem_id="add-q-status")

            # -------------------------------------------------- Tab 2: 教案规划
            with gr.Tab(I18N["zh"]["tab_lesson"], id="tab-lesson") as tab_lesson:
                _lp_year0 = "Year 11"
                _lp_mods0 = lp_modules(_lp_year0)
                _lp_mod0 = _lp_mods0[0] if _lp_mods0 else None
                _lp_dps0 = lp_dot_point_choices(_lp_year0, _lp_mod0) if _lp_mod0 else []

                with gr.Group(elem_classes="panel"):
                    lp_year = gr.Radio(["Year 11", "Year 12"], value=_lp_year0,
                                       label=I18N["zh"]["lp_year_label"], elem_id="lp-year")
                    lp_module = gr.Dropdown(choices=_lp_mods0, value=_lp_mod0,
                                            label=I18N["zh"]["lp_module_label"], elem_id="lp-module")
                    lp_hint = gr.Markdown(I18N["zh"]["lp_dp_hint"], elem_id="lp-hint")
                    lp_dots = gr.CheckboxGroup(choices=_lp_dps0, value=[],
                                               label=I18N["zh"]["lp_dp_label"],
                                               show_select_all=True, elem_id="lp-dots")
                    lp_counter = gr.Markdown(I18N["zh"]["lp_dp_count"].format(n=0), elem_id="lp-counter")

                with gr.Group(elem_classes="panel"):
                    lp_ref = gr.Textbox(label=I18N["zh"]["lp_ref_label"], lines=6,
                                        placeholder=I18N["zh"]["lp_ref_ph"], elem_id="lp-ref")
                    lp_dur = gr.Slider(minimum=30, maximum=120, step=5, value=60,
                                       label=I18N["zh"]["lp_dur_label"], elem_id="lp-dur")

                lp_btn = gr.Button(I18N["zh"]["lp_gen_btn"], variant="primary",
                                   elem_id="lp-gen-btn", size="lg")
                lp_result = gr.HTML(render_plan_empty("zh"), elem_id="lp-result")

            # -------------------------------------------------- Tab 3: 学生
            with gr.Tab(I18N["zh"]["tab_students"], id="tab-students") as tab_students:
                _st_students0 = store_db.list_students()
                _st_choices0 = st_student_choices(_st_students0, "zh")

                # ---------- 区块 A：追踪画像 ----------
                with gr.Group(elem_classes="panel"):
                    st_student = gr.Dropdown(
                        choices=_st_choices0,
                        value=_st_choices0[0][1] if _st_choices0 else None,
                        label=I18N["zh"]["st_student_label"], elem_id="st-student")
                    st_analyze_btn = gr.Button(I18N["zh"]["st_analyze_btn"], variant="primary",
                                               elem_id="st-analyze-btn", size="lg")
                    st_profile = gr.HTML(render_profile_empty("zh"), elem_id="st-profile")

                # ---------- 区块 B：报告评语 ----------
                with gr.Group(elem_classes="panel"):
                    st_period = gr.Textbox(label=I18N["zh"]["st_period_label"],
                                           value="Term 3 2026", placeholder=I18N["zh"]["st_period_ph"],
                                           elem_id="st-period")
                    st_notes = gr.Textbox(label=I18N["zh"]["st_notes_label"], lines=4,
                                          placeholder=I18N["zh"]["st_notes_ph"], elem_id="st-notes")
                    st_gen_btn = gr.Button(I18N["zh"]["st_gen_btn"], variant="primary",
                                           elem_id="st-gen-btn", size="lg")
                    st_comment = gr.HTML(render_report_empty("zh"), elem_id="st-comment")
                    st_save_btn = gr.Button(I18N["zh"]["st_save_btn"], elem_id="st-save-btn",
                                            interactive=False)
                    st_status = gr.Markdown("", elem_id="st-status")

        # ---------- 语言切换 ----------
        def set_lang(lang_choice, cur_qid, lp_selected):
            lang = "en" if lang_choice == "EN" else "zh"
            L = I18N[lang]
            updates = {
                # re-read the bank so custom questions saved earlier stay listed
                q_dropdown: gr.update(choices=q_choices(load_questions(), lang), value=cur_qid,
                                      label=L["q_label"], info=None),
                ans_box: gr.update(label=L["ans_label"], placeholder=L["ans_ph"]),
                ex_radio: gr.update(choices=[L["ex_good"], L["ex_bad"]], label=L["ex_label"]),
                mark_btn: gr.update(value=L["mark_btn"]),
                raw_accord: gr.update(label=L["raw_label"]),
                q_preview: gr.update(value=q_preview_md(cur_qid, lang)),
                title_md: gr.update(value=f'<div class="logo"><span class="mark">AI</span><span class="brandname">CoachAI</span> '
                                          f'<span class="hsc-tag">HSC</span></div>'
                                          f'<div class="sub">{L["subtitle"]}</div>'),
                add_accord: gr.update(label=L["add_q_label"]),
                cq_note: gr.update(value=L["add_q_note"]),
                cq_text: gr.update(label=L["add_q_text_label"], placeholder=L["add_q_text_ph"]),
                cq_marks: gr.update(label=L["add_q_marks_label"]),
                cq_criteria: gr.update(label=L["add_q_criteria_label"], placeholder=L["add_q_criteria_ph"]),
                cq_sample: gr.update(label=L["add_q_sample_label"], placeholder=L["add_q_sample_ph"]),
                cq_save: gr.update(value=L["add_q_btn"]),
                # ---- Phase 4: tabs + lesson planner ----
                tab_mark: gr.update(label=L["tab_mark"]),
                tab_lesson: gr.update(label=L["tab_lesson"]),
                lp_year: gr.update(label=L["lp_year_label"]),
                lp_module: gr.update(label=L["lp_module_label"]),
                lp_hint: gr.update(value=L["lp_dp_hint"]),
                lp_dots: gr.update(label=L["lp_dp_label"]),
                lp_counter: gr.update(value=L["lp_dp_count"].format(n=len(lp_selected or []))),
                lp_ref: gr.update(label=L["lp_ref_label"], placeholder=L["lp_ref_ph"]),
                lp_dur: gr.update(label=L["lp_dur_label"]),
                lp_btn: gr.update(value=L["lp_gen_btn"]),
                # ---- Phase 5: students tab ----
                tab_students: gr.update(label=L["tab_students"]),
                st_student: gr.update(label=L["st_student_label"], info=None),
                st_analyze_btn: gr.update(value=L["st_analyze_btn"]),
                st_period: gr.update(label=L["st_period_label"]),
                st_notes: gr.update(label=L["st_notes_label"], placeholder=L["st_notes_ph"]),
                st_gen_btn: gr.update(value=L["st_gen_btn"]),
                st_save_btn: gr.update(value=L["st_save_btn"]),
            }
            order = (q_dropdown, ans_box, ex_radio, mark_btn, raw_accord, q_preview, title_md,
                     add_accord, cq_note, cq_text, cq_marks, cq_criteria, cq_sample, cq_save,
                     tab_mark, tab_lesson, lp_year, lp_module, lp_hint, lp_dots, lp_counter,
                     lp_ref, lp_dur, lp_btn, tab_students, st_student, st_analyze_btn,
                     st_period, st_notes, st_gen_btn, st_save_btn)
            return [lang, *[updates[c] for c in order]]

        lang_radio.change(fn=set_lang,
                          inputs=[lang_radio, qid_state, lp_dots],
                          outputs=[lang_state, q_dropdown, ans_box, ex_radio, mark_btn, raw_accord,
                                   q_preview, title_md, add_accord, cq_note, cq_text, cq_marks,
                                   cq_criteria, cq_sample, cq_save, tab_mark, tab_lesson,
                                   lp_year, lp_module, lp_hint, lp_dots, lp_counter,
                                   lp_ref, lp_dur, lp_btn, tab_students, st_student,
                                   st_analyze_btn, st_period, st_notes, st_gen_btn, st_save_btn])

        # ---------- 示例答案填充 ----------
        def on_q_change(qid, lang):
            if not qid:
                return qid, gr.update(value=qid), ""
            return qid, gr.update(value=qid), q_preview_md(qid, lang)

        def fill_example(ex_choice, qid, lang):
            L = I18N[lang]
            if not ex_choice or not qid:
                return gr.update(), None
            kind = "good" if ex_choice == L["ex_good"] else "bad"
            samples = load_examples().get(qid, {}).get(kind)
            if not samples:
                try:
                    gr.Info(L["no_ex"].format(kind=L["no_ex_good" if kind == "good" else "no_ex_bad"]))
                except Exception:  # noqa: BLE001
                    pass
                return gr.update(), None
            return gr.update(value=samples[0]), None

        ex_radio.select(fn=fill_example, inputs=[ex_radio, qid_state, lang_state],
                        outputs=[ans_box, ex_radio])

        # ---------- 自建题目：保存 + 刷新下拉框 ----------
        def on_save_question(text, marks, criteria, sample, lang, cur_qid):
            """Persist a teacher-authored question, refresh the dropdown and preview."""
            L = I18N.get(lang, I18N["en"])
            try:
                qid = save_custom_question(
                    BASE_DIR / "data",
                    {"text": text, "marks": marks, "criteria": criteria,
                     "sample_answer": sample},
                )
            except ValueError as exc:  # validation failed -> nothing was written
                msg = f'{L["add_q_err"]} ({exc})'
                try:
                    gr.Warning(msg)
                except Exception:  # noqa: BLE001
                    pass
                keep = gr.update()
                return (keep, cur_qid, keep, msg, keep, keep, keep, keep)
            questions_now = load_questions()
            msg = L["add_q_ok"].format(qid=qid)
            try:
                gr.Info(msg)
            except Exception:  # noqa: BLE001
                pass
            return (gr.update(choices=q_choices(questions_now, lang), value=qid),
                    qid, q_preview_md(qid, lang), msg,
                    "", None, "", "")

        cq_save.click(fn=on_save_question,
                      inputs=[cq_text, cq_marks, cq_criteria, cq_sample, lang_state, qid_state],
                      outputs=[q_dropdown, qid_state, q_preview, cq_status,
                               cq_text, cq_marks, cq_criteria, cq_sample])

        # ---------- 批改 ----------
        def on_mark(qid, answer, lang):
            html_out, raw = mark_answer_safe(qid, answer, lang)
            return html_out, raw

        mark_btn.click(fn=on_mark, inputs=[qid_state, ans_box, lang_state],
                       outputs=[result_md, raw_json])

        q_dropdown.change(fn=on_q_change, inputs=[q_dropdown, lang_state],
                          outputs=[qid_state, q_dropdown, q_preview])

        # ---------- 教案规划：联动 + 生成 ----------
        def on_lp_year_change(year, lang):
            """Year change -> refresh module dropdown and dot point checkboxes."""
            mods = lp_modules(year)
            first = mods[0] if mods else None
            dps = lp_dot_point_choices(year, first) if first else []
            return (gr.update(choices=mods, value=first),
                    gr.update(choices=dps, value=[]),
                    lp_selection_note([], lang))

        def on_lp_module_change(year, focus_area, lang):
            """Module change -> refresh dot point checkboxes (selection cleared)."""
            return (gr.update(choices=lp_dot_point_choices(year, focus_area), value=[]),
                    lp_selection_note([], lang))

        lp_year.change(fn=on_lp_year_change, inputs=[lp_year, lang_state],
                       outputs=[lp_module, lp_dots, lp_counter])
        lp_module.change(fn=on_lp_module_change, inputs=[lp_year, lp_module, lang_state],
                         outputs=[lp_dots, lp_counter])
        lp_dots.change(fn=lp_selection_note, inputs=[lp_dots, lang_state],
                       outputs=[lp_counter])

        lp_btn.click(fn=generate_plan_safe,
                     inputs=[lp_dots, lp_ref, lp_year, lp_dur, lp_module, lang_state],
                     outputs=[lp_result])

        # ---------- 学生（Phase 5）：切换学生清空结果 / 分析 / 生成 / 保存 ----------
        def on_student_change(student_id, lang):
            """Switching student resets both result areas to their placeholders."""
            return (render_profile_empty(lang), render_report_empty(lang), "", None,
                    gr.update(interactive=False))

        st_student.change(fn=on_student_change, inputs=[st_student, lang_state],
                          outputs=[st_profile, st_comment, st_status, st_last_report,
                                   st_save_btn])

        st_analyze_btn.click(fn=st_analyze_safe, inputs=[st_student, lang_state],
                             outputs=[st_profile])

        st_gen_btn.click(fn=st_generate_safe,
                         inputs=[st_student, st_period, st_notes, lang_state],
                         outputs=[st_comment, st_last_report, st_save_btn])

        st_save_btn.click(fn=st_save_safe, inputs=[st_last_report, lang_state],
                          outputs=[st_status, st_save_btn])

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.queue(default_concurrency_limit=4).launch(
        server_name="127.0.0.1", server_port=7860, show_error=True, quiet=False,
        theme=GradioDefault(primary_hue=gradio_colors.blue, neutral_hue=gradio_colors.gray),
        css=PAGE_CSS)
