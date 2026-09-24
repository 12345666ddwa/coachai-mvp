#!/usr/bin/env python3
"""UI v2 upgrade: replace PAGE_CSS block, render_result_html, err_card, header markdown.
Function/architecture unchanged - visual layer only."""
import re

src = open('app.py', encoding='utf-8').read()

# ---------------------------------------------------------------- 1. PAGE_CSS
NEW_CSS = '''PAGE_CSS = """
:root { --paper:#FAFAF7; --ink:#1A2332; --blue:#1F4E79; --blue-hover:#143A5C;
        --orange:#E69F00; --orange-deep:#C77F00; --line:#E8E2D8; --card:#FFFFFF;
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
#mark-btn { background: linear-gradient(180deg, #245A8C, var(--blue)) !important;
    border: none !important; border-radius: 8px !important; font-weight: 700 !important;
    padding: 15px 56px !important; font-size: 1.05em !important; letter-spacing: .3px;
    box-shadow: 0 4px 14px rgba(31,78,121,.28) !important; transition: all .18s ease !important; }
#mark-btn:hover { transform: translateY(-1px); box-shadow: 0 8px 22px rgba(31,78,121,.35) !important; }
#mark-btn:active { transform: translateY(0); box-shadow: 0 2px 8px rgba(31,78,121,.25) !important; }
#mark-btn:disabled { opacity:.55 !important; }

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

@media (max-width: 760px) {
    .gradio-container { padding: 0 4px 40px !important; }
    #coach-header { padding: 22px 20px 18px; }
    .panel { padding: 18px 16px; }
    .coach-result { padding: 20px 16px; }
    .coach-result .r-score .big { font-size: 2.6em; }
    .conf-ring { width: 76px; height: 76px; }
    .conf-ring .ring-in { width: 58px; height: 58px; }
}
"""'''

src = re.sub(r'PAGE_CSS = """.*?"""', NEW_CSS, src, count=1, flags=re.DOTALL)
print('PAGE_CSS replaced:', NEW_CSS in src)

# ---------------------------------------------------------------- 2. header markdown (both occurrences)
OLD_HEADER_OLD = '<div class="logo"><span class="mark">AI</span> CoachAI '
NEW_HEADER_OLD = '<div class="logo"><span class="mark">AI</span><span class="brandname">CoachAI</span> '
# the f-string template uses f'...' so braces escaped; we replace textual pieces
src = src.replace("f'<div class=\"logo\"><span class=\"mark\">AI</span> CoachAI '",
                  "f'<div class=\"logo\"><span class=\"mark\">AI</span><span class=\"brandname\">CoachAI</span> '")
src = src.replace("'<div class=\"logo\"><span class=\"mark\">🎓</span> CoachAI '", "")  # safety no-op
# subtitle line stays as-is (sub div). Ensure HSC tag keeps its styling but switch to .hsc-tag class
src = src.replace("f'<span style=\"color:#E69F00;font-size:.62em;font-weight:700;border:1.5px solid #E69F00;'\n"
                  "                                          f'border-radius:4px;padding:2px 8px;vertical-align:middle\">HSC</span></div>'",
                  "f'<span class=\"hsc-tag\">HSC</span></div>'")
print('header markdown updated:', "brandname" in src)

# ---------------------------------------------------------------- 3. render_result_html
RENDER_NEW = '''def render_result_html(res: dict, qid: str, lang: str) -> str:
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
    h.append(f'<div class="r-score"><span class="big">{marks if marks is not None else "-"}</span>'
             f'<span class="max">{suffix}</span></div>')
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
    return "".join(h)'''

src = re.sub(r'def render_result_html\(res: dict, qid: str, lang: str\) -> str:.*?(?=\ndef err_card|\ndef err_card\()',
             RENDER_NEW, src, count=1, flags=re.DOTALL)
print('render_result_html replaced:', 'coach-result' in src)

# ---------------------------------------------------------------- 4. i18n confidence-level keys
I18N_ADD = [
    ('        "conf": "置信度",\n', '        "conf": "置信度",\n'
     '        "confHigh": "高置信度",\n        "confMedium": "中置信度",\n        "confLow": "低置信度",\n'),
    ('        "conf": "Confidence",\n', '        "conf": "Confidence",\n'
     '        "confHigh": "High confidence",\n        "confMedium": "Medium confidence",\n        "confLow": "Low confidence",\n'),
]
for old, new in I18N_ADD:
    if old in src:
        src = src.replace(old, new, 1)
        print('i18n keys added:', old.strip()[:40])
    else:
        print('i18n anchor NOT FOUND:', old[:40])

# ---------------------------------------------------------------- 5. err_card -> coach-error class
ERR_OLD = '''def err_card(title: str, hint: str = "") -> str:
    return (f'<div style="background:#FBEAEA;border:1.5px solid #C62828;border-radius:6px;padding:14px 16px;'
            f'font-family:Segoe UI,PingFang SC,Microsoft YaHei,sans-serif">'
            f'<div style="color:#C62828;font-weight:700">{title}</div>'
            + (f'<div style="color:#6B7684;font-size:.88em;margin-top:6px">{hint}</div>' if hint else "") + "</div>")'''
ERR_NEW = '''def err_card(title: str, hint: str = "") -> str:
    html = f'<div class="coach-error">{title}'
    if hint:
        html += f'<div class="hint">{hint}</div>'
    return html + "</div>"'''
if ERR_OLD in src:
    src = src.replace(ERR_OLD, ERR_NEW, 1)
    print('err_card replaced')
else:
    print('err_card NOT FOUND - skipping (may already be replaced)')

open('app.py', 'w', encoding='utf-8').write(src)
print('app.py written')
