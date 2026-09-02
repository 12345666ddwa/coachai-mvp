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

import json
import sys
from pathlib import Path

import gradio as gr
from gradio.themes import Default as GradioDefault, colors as gradio_colors

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = BASE_DIR / "data" / "questions.json"
GOLDEN_PATH = BASE_DIR / "tests" / "golden_set.json"

# ---------------------------------------------------------------- i18n 文案
I18N = {
    "zh": {
        "title": "CoachAI — HSC Enterprise Computing 智能批改",
        "subtitle": "选一道题，写下你的答案，AI 按官方评分标准即时批改",
        "q_label": "选择题目",
        "q_ph": "从题库选择一道题…",
        "ans_label": "你的答案",
        "ans_ph": "在此输入 / 粘贴你的答案…",
        "ex_label": "快速示例",
        "ex_good": "加载示例答案：好答案",
        "ex_bad": "加载示例答案：差答案",
        "no_ex": "该题没有可用的{kind}示例，请手动输入答案。",
        "no_ex_good": "好",
        "no_ex_bad": "差",
        "mark_btn": "🚀 开始批改",
        "marking": "AI 正在批改…",
        "err_empty": "⚠️ 请先选择题目并输入答案，再开始批改。",
        "err_backend": "⚠️ 批改引擎尚未就绪：无法导入 `graphs.mark_graph`。",
        "err_backend_hint": "请先在后端实现 `mark_answer(question_id, student_answer)`（见 app.py 头部约定），或确认运行目录为项目根。",
        "err_unknown": "⚠️ 批改服务返回异常：",
        "res_title": "批改结果",
        "status_approved": "✅ 已批改",
        "status_flagged": "🚩 需人工复核",
        "status_error": "❌ 批改出错",
        "conf": "置信度",
        "attempts": "答题次数",
        "fb_good": "✅ 优点",
        "fb_improve": "💡 改进建议",
        "fb_rule": "📌 规则提示",
        "fb_other": "📝 反馈",
        "flags_head": "🚩 疑点标记",
        "just_head": "批改说明",
        "raw_label": "原始返回（JSON）",
        "marks_unit": "分",
        "q_marks_suffix": "分",
        "footer": "CoachAI · 基于 NESA 官方评分标准",
        "err_import_title": "后端批改模块未就绪",
    },
    "en": {
        "title": "CoachAI — HSC Enterprise Computing AI Marking",
        "subtitle": "Pick a question, write your answer, get instant AI feedback against official criteria",
        "q_label": "Select question",
        "q_ph": "Pick a question from the bank…",
        "ans_label": "Your answer",
        "ans_ph": "Type / paste your answer here…",
        "ex_label": "Quick examples",
        "ex_good": "Load example: strong answer",
        "ex_bad": "Load example: weak answer",
        "no_ex": "No {kind} example available for this question — please type your own answer.",
        "no_ex_good": "good",
        "no_ex_bad": "bad",
        "mark_btn": "🚀 Mark my answer",
        "marking": "AI is marking…",
        "err_empty": "⚠️ Please select a question and enter an answer first.",
        "err_backend": "⚠️ Marking engine not ready: cannot import `graphs.mark_graph`.",
        "err_backend_hint": "Implement `mark_answer(question_id, student_answer)` in the backend (contract in app.py header), or run from the project root.",
        "err_unknown": "⚠️ Marking service returned an error:",
        "res_title": "Marking result",
        "status_approved": "✅ Approved",
        "status_flagged": "🚩 Flagged for review",
        "status_error": "❌ Marking failed",
        "conf": "Confidence",
        "attempts": "Attempts",
        "fb_good": "✅ Strengths",
        "fb_improve": "💡 To improve",
        "fb_rule": "📌 Marking rule",
        "fb_other": "📝 Feedback",
        "flags_head": "🚩 Flags",
        "just_head": "Justification",
        "raw_label": "Raw response (JSON)",
        "marks_unit": "",
        "q_marks_suffix": "marks",
        "footer": "CoachAI · aligned with NESA official marking guidelines",
        "err_import_title": "Backend marking module unavailable",
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
    """读取题库；失败返回 []。"""
    try:
        with open(QUESTIONS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("questions", [])
    except Exception as e:  # noqa: BLE001
        print(f"[app] 题库读取失败: {e}", file=sys.stderr)
        return []


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

# ---------------------------------------------------------------- 渲染
def render_result_html(res: dict, qid: str, lang: str) -> str:
    """把 mark_answer 返回 dict 渲染成卡片 HTML（内联样式，无需外部 CSS）。"""
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
    bg, _soft, border = STATUS_STYLE.get(status, STATUS_STYLE["error"])
    stat_txt = L.get(f"status_{status}", status)

    h = ['<div style="background:#fff;border:1.5px solid #E3E7EC;border-radius:16px;'
         'padding:20px;box-shadow:0 2px 12px rgba(26,35,50,.08);font-family:Segoe UI,PingFang SC,Microsoft YaHei,sans-serif">']

    if status == "error":
        msg = (res.get("message") or res.get("error") or "unknown error")
        h.append(f'<div style="color:#C62828;font-weight:700;font-size:1.1em">❌ {msg}</div>'
                 f'<div style="color:#6B7684;font-size:.9em;margin-top:6px">status=error · {qid}</div>')
        h.append("</div>")
        return "".join(h)

    # 顶部：大分数 + 徽章
    h.append('<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">')
    unit = L["marks_unit"]
    suffix = f"/ {max_marks} {unit}".strip() if max_marks is not None else ""
    h.append(f'<div style="color:#1F4E79;font-size:3em;font-weight:800;line-height:1">'
             f'{marks if marks is not None else "–"}'
             f'<span style="font-size:.4em;color:#6B7684;font-weight:600"> {suffix}</span></div>')
    badges = []
    c_conf = CONF_COLOR.get(str(res.get("confidence_level", "")), "#6B7684")
    conf_pct = res.get("confidence_pct")
    conf_txt = f'{L["conf"]} {conf_pct}%' if conf_pct is not None else L["conf"]
    badges.append(f'<span style="border:1.5px solid {c_conf};color:{c_conf};background:#fff;'
                  f'border-radius:20px;padding:4px 12px;font-size:.78em;font-weight:700">{conf_txt}</span>')
    attempts = res.get("attempts")
    if attempts is not None:
        badges.append(f'<span style="border:1.5px solid #6B7684;color:#6B7684;border-radius:20px;'
                      f'padding:4px 12px;font-size:.78em;font-weight:700">{L["attempts"]}: {attempts}</span>')
    h.append('<div style="display:flex;gap:8px;flex-wrap:wrap">' + "".join(badges) + "</div>")
    h.append("</div>")

    # 状态横幅
    h.append(f'<div style="margin-top:12px;background:{bg}1A;border:1.5px solid {border};color:{bg};'
             f'border-radius:10px;padding:8px 14px;font-weight:700;font-size:.9em">{stat_txt}</div>')

    # 逐条反馈
    fb = res.get("feedback") or []
    for item in fb:
        if isinstance(item, str):
            item = {"type": "other", "text": item}
        ftype = str(item.get("type", "other")).lower()
        color, soft = FB_TYPE.get(ftype, ("#6B7684", "#F4F6F8"))
        head = L.get(f"fb_{ftype}", L["fb_other"])
        h.append(f'<div style="margin-top:10px;background:{soft};border-left:4px solid {color};'
                 f'border-radius:8px;padding:10px 14px;font-size:.92em;line-height:1.55">'
                 f'<span style="font-weight:700;color:{color}">{head}</span><br>{item.get("text", "")}</div>')

    # flags
    flags = res.get("flags") or []
    if flags:
        h.append(f'<div style="margin-top:12px;background:#FBEAEA;border:1px solid #C62828;border-radius:8px;'
                 f'padding:10px 14px;font-size:.9em;color:#8b1a1a">'
                 f'<span style="font-weight:700">{L["flags_head"]}</span><ul style="margin:6px 0 0 18px">'
                 + "".join(f"<li>{f}</li>" for f in flags) + "</ul></div>")

    just = res.get("justification")
    if just:
        h.append(f'<div style="margin-top:12px;color:#6B7684;font-size:.85em;border-top:1px dashed #E3E7EC;'
                 f'padding-top:10px"><b style="color:#1F4E79">{L["just_head"]}</b><br>{just}</div>')

    h.append("</div>")
    return "".join(h)


def err_card(title: str, hint: str = "") -> str:
    return (f'<div style="background:#FBEAEA;border:1.5px solid #C62828;border-radius:12px;padding:14px 16px;'
            f'font-family:Segoe UI,PingFang SC,Microsoft YaHei,sans-serif">'
            f'<div style="color:#C62828;font-weight:700">{title}</div>'
            + (f'<div style="color:#6B7684;font-size:.88em;margin-top:6px">{hint}</div>' if hint else "") + "</div>")

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
    try:
        res = _mark(qid, answer)
    except Exception as e:  # noqa: BLE001
        print(f"[app] mark_answer 调用失败: {e}", file=sys.stderr)
        return err_card(f'{L["err_unknown"]} {e}'), {"error": str(e)}
    if not isinstance(res, dict):
        return err_card(f'{L["err_unknown"]} unexpected type {type(res).__name__}'), {"raw": res}
    if res.get("status") == "error":
        msg = res.get("message") or res.get("error") or "unknown error"
        return err_card(f'{L["status_error"]} — {msg}'), res
    return render_result_html(res, qid, lang), res

# ---------------------------------------------------------------- Gradio 界面
PAGE_CSS = """
:root { --paper:#FAFAF7; --ink:#1A2332; --blue:#1F4E79; --blue-hover:#16395c;
        --orange:#E69F00; --line:#E3E7EC; --card:#FFFFFF; }
body, .gradio-container { background: var(--paper) !important; color: var(--ink); }
.gradio-container { max-width: 900px !important; margin: 0 auto !important;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                                 "PingFang SC", "Microsoft YaHei", sans-serif !important; }
#coach-header { background: var(--card); border:1px solid var(--line); border-radius:16px;
                box-shadow: 0 2px 12px rgba(26,35,50,.08); padding: 20px 24px; margin-top: 14px; }
#coach-header .logo { display:inline-flex; align-items:center; gap:10px; font-weight:800; font-size:1.25em; color:var(--ink); }
#coach-header .logo .mark { background:var(--blue); color:#fff; border-radius:9px; width:34px; height:34px;
                            display:inline-flex; align-items:center; justify-content:center; font-size:.9em; }
#coach-header .sub { color:#6B7684; font-size:.92em; margin-top:4px; }
#lang-switch button { border-radius: 20px !important; font-weight:600 !important; }
#lang-switch .selected { background: var(--blue) !important; border-color: var(--blue) !important; color:#fff !important; }
#lang-switch button:not(.selected) { background:var(--card) !important; color:var(--ink) !important;
                                     border:1px solid var(--line) !important; }
.panel { background: var(--card); border:1px solid var(--line); border-radius:16px;
         box-shadow: 0 2px 12px rgba(26,35,50,.08); padding: 16px 18px; }
#mark-btn { background: var(--blue) !important; border: none !important; border-radius: 30px !important;
            font-weight:700 !important; padding: 12px 44px !important; font-size:1.02em !important; }
#mark-btn:hover { background: var(--blue-hover) !important; box-shadow: 0 6px 18px rgba(31,78,121,.3) !important; }
#mark-btn:disabled { opacity:.45; }
textarea:focus, input:focus { border-color: var(--blue) !important; box-shadow: 0 0 0 1px var(--blue) !important; }
footer { display: none !important; }
@media (max-width: 640px) {
  .gradio-container { max-width: 100% !important; padding: 0 6px !important; }
  #coach-header { padding: 14px !important; }
  #coach-header .logo { font-size: 1.05em !important; }
}
"""

def build_ui() -> gr.Blocks:
    questions = load_questions()
    with gr.Blocks(title="CoachAI") as demo:
        lang_state = gr.State("zh")
        qid_state = gr.State(questions[0]["id"] if questions else None)

        # ---------- 顶部：品牌 + 语言切换 ----------
        with gr.Row(elem_id="coach-header"):
            with gr.Column(scale=4):
                title_md = gr.Markdown(
                    f'<div class="logo"><span class="mark">🎓</span> CoachAI '
                    f'<span style="color:#E69F00;font-size:.62em;font-weight:700;border:1.5px solid #E69F00;'
                    f'border-radius:20px;padding:2px 8px;vertical-align:middle">HSC</span></div>'
                    f'<div class="sub">{I18N["zh"]["subtitle"]}</div>')
            with gr.Column(scale=1, elem_id="lang-switch"):
                lang_radio = gr.Radio(["中文", "EN"], value="中文", show_label=False,
                                      interactive=True, elem_id="lang-select")

        # ---------- 1. 选题 ----------
        with gr.Group(elem_classes="panel"):
            q_dropdown = gr.Dropdown(choices=q_choices(questions, "zh"), value=questions[0]["id"] if questions else None,
                                     label=I18N["zh"]["q_label"], elem_id="q-drop")
            q_preview = gr.Markdown("", visible=False)

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

        # ---------- 语言切换 ----------
        def set_lang(lang_choice, cur_qid):
            lang = "en" if lang_choice == "EN" else "zh"
            L = I18N[lang]
            updates = {
                q_dropdown: gr.update(choices=q_choices(questions, lang), value=cur_qid,
                                      label=L["q_label"], info=None),
                ans_box: gr.update(label=L["ans_label"], placeholder=L["ans_ph"]),
                ex_radio: gr.update(choices=[L["ex_good"], L["ex_bad"]], label=L["ex_label"]),
                mark_btn: gr.update(value=L["mark_btn"]),
                raw_accord: gr.update(label=L["raw_label"]),
                title_md: gr.update(value=f'<div class="logo"><span class="mark">🎓</span> CoachAI '
                                          f'<span style="color:#E69F00;font-size:.62em;font-weight:700;border:1.5px solid #E69F00;'
                                          f'border-radius:20px;padding:2px 8px;vertical-align:middle">HSC</span></div>'
                                          f'<div class="sub">{L["subtitle"]}</div>'),
            }
            return [lang, *[updates[c] for c in (q_dropdown, ans_box, ex_radio, mark_btn, raw_accord, title_md)]]

        lang_radio.change(fn=set_lang,
                          inputs=[lang_radio, qid_state],
                          outputs=[lang_state, q_dropdown, ans_box, ex_radio, mark_btn, raw_accord, title_md])

        # ---------- 示例答案填充 ----------
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

        # ---------- 批改 ----------
        def on_mark(qid, answer, lang):
            html, raw = mark_answer_safe(qid, answer, lang)
            return html, raw

        mark_btn.click(fn=on_mark, inputs=[qid_state, ans_box, lang_state],
                       outputs=[result_md, raw_json])

        q_dropdown.change(fn=lambda qid: (qid, gr.update(value=qid)), inputs=[q_dropdown],
                          outputs=[qid_state, q_dropdown])

    return demo


if __name__ == "__main__":
    app = build_ui()
    app.queue(default_concurrency_limit=4).launch(
        server_name="127.0.0.1", server_port=7860, show_error=True, quiet=False,
        theme=GradioDefault(primary_hue=gradio_colors.blue, neutral_hue=gradio_colors.gray),
        css=PAGE_CSS)
