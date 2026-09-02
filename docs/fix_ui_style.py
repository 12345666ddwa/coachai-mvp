#!/usr/bin/env python3
"""Strip emoji + flatten corners + widen layout in app.py UI."""
src = open('app.py', encoding='utf-8').read()
orig = src

repl = [
    ('"mark_btn": "🚀 开始批改"', '"mark_btn": "开始批改"'),
    ('"mark_btn": "🚀 Mark my answer"', '"mark_btn": "Mark my answer"'),
    ('"err_empty": "⚠️ 请先选择题目并输入答案，再开始批改。"', '"err_empty": "请先选择题目并输入答案，再开始批改。"'),
    ('"err_empty": "⚠️ Please select a question and enter an answer first."', '"err_empty": "Please select a question and enter an answer first."'),
    ('"err_backend": "⚠️ 批改引擎尚未就绪：无法导入 `graphs.mark_graph`。"', '"err_backend": "批改引擎尚未就绪：无法导入 graphs.mark_graph。"'),
    ('"err_backend": "⚠️ Marking engine not ready: cannot import `graphs.mark_graph`."', '"err_backend": "Marking engine not ready: cannot import graphs.mark_graph."'),
    ('"err_unknown": "⚠️ 批改服务返回异常："', '"err_unknown": "批改服务返回异常："'),
    ('"err_unknown": "⚠️ Marking service returned an error:"', '"err_unknown": "Marking service returned an error:"'),
    ('"status_approved": "✅ 已批改"', '"status_approved": "已批改"'),
    ('"status_approved": "✅ Approved"', '"status_approved": "Approved"'),
    ('"status_flagged": "🚩 需人工复核"', '"status_flagged": "需人工复核"'),
    ('"status_flagged": "🚩 Flagged for review"', '"status_flagged": "Flagged for review"'),
    ('"status_error": "❌ 批改出错"', '"status_error": "批改出错"'),
    ('"status_error": "❌ Marking failed"', '"status_error": "Marking failed"'),
    ('"fb_good": "✅ 优点"', '"fb_good": "优点"'),
    ('"fb_good": "✅ Strengths"', '"fb_good": "Strengths"'),
    ('"fb_improve": "💡 改进建议"', '"fb_improve": "改进建议"'),
    ('"fb_improve": "💡 To improve"', '"fb_improve": "To improve"'),
    ('"fb_rule": "📌 规则提示"', '"fb_rule": "规则提示"'),
    ('"fb_rule": "📌 Marking rule"', '"fb_rule": "Marking rule"'),
    ('"fb_other": "📝 反馈"', '"fb_other": "反馈"'),
    ('"fb_other": "📝 Feedback"', '"fb_other": "Feedback"'),
    ('"flags_head": "🚩 疑点标记"', '"flags_head": "疑点标记"'),
    ('"flags_head": "🚩 Flags"', '"flags_head": "Flags"'),
    ('font-weight:700;font-size:1.1em">❌ {msg}</div>', 'font-weight:700;font-size:1.1em">{msg}</div>'),
    ('<span class="mark">🎓</span>', '<span class="mark">AI</span>'),
]
for old, new in repl:
    n = src.count(old)
    if n:
        src = src.replace(old, new)
        print(f'replaced {n}x: {old[:48]}')
    else:
        print(f'NOT FOUND: {old[:60]}')

css_repl = [
    ('.gradio-container { max-width: 900px !important; margin: 0 auto !important;',
     '.gradio-container { max-width: 1180px !important; margin: 0 auto !important;'),
    ('#coach-header { background: var(--card); border:1px solid var(--line); border-radius:16px;\n                box-shadow: 0 2px 12px rgba(26,35,50,.08); padding: 20px 24px; margin-top: 14px; }',
     '#coach-header { background: var(--card); border:1px solid var(--line); border-radius:6px;\n                box-shadow: 0 1px 8px rgba(26,35,50,.06); padding: 28px 32px; margin-top: 24px; }'),
    ('#coach-header .logo .mark { background:var(--blue); color:#fff; border-radius:9px; width:34px; height:34px;\n                            display:inline-flex; align-items:center; justify-content:center; font-size:.9em; }',
     '#coach-header .logo .mark { background:var(--blue); color:#fff; border-radius:6px; width:38px; height:38px;\n                            display:inline-flex; align-items:center; justify-content:center; font-size:.85em; font-weight:800; letter-spacing:.5px; }'),
    ('.panel { background: var(--card); border:1px solid var(--line); border-radius:16px;\n         box-shadow: 0 2px 12px rgba(26,35,50,.08); padding: 16px 18px; }',
     '.panel { background: var(--card); border:1px solid var(--line); border-radius:6px;\n         box-shadow: 0 1px 8px rgba(26,35,50,.05); padding: 26px 30px; }'),
    ('#mark-btn { background: var(--blue) !important; border: none !important; border-radius: 30px !important;\n            font-weight:700 !important; padding: 12px 44px !important; font-size:1.02em !important; }',
     '#mark-btn { background: var(--blue) !important; border: none !important; border-radius: 6px !important;\n            font-weight:700 !important; padding: 14px 52px !important; font-size:1.05em !important; }'),
    ('border-radius:20px;padding:2px 8px;vertical-align:middle">HSC</span>',
     'border-radius:4px;padding:2px 8px;vertical-align:middle">HSC</span>'),
    ('footer { display: none !important; }',
     '#q-preview { background:#F7F9FB; border:1px solid var(--line); border-radius:6px; padding:16px 18px;\n                  line-height:1.65; font-size:.95em; color:#33404F; margin-top:2px; }\n'
     '#q-preview .q-meta { color:#6B7684; font-size:.78em; font-weight:700; letter-spacing:.4px; text-transform:uppercase; margin-bottom:6px; }\n'
     'footer { display: none !important; }'),
]
for old, new in css_repl:
    if old in src:
        src = src.replace(old, new)
        print('CSS replaced:', old[:60])
    else:
        print('CSS NOT FOUND:', old[:70])

inline = [
    ("background:#fff;border:1.5px solid #E3E7EC;border-radius:16px;", "background:#fff;border:1.5px solid #E3E7EC;border-radius:6px;"),
    ("border-radius:20px;padding:4px 12px;font-size:.78em;font-weight:700", "border-radius:4px;padding:5px 12px;font-size:.78em;font-weight:700"),
    ("border-radius:10px;padding:8px 14px;font-weight:700;font-size:.9em", "border-radius:4px;padding:8px 14px;font-weight:700;font-size:.9em"),
    ("border-radius:8px;padding:10px 14px;font-size:.92em;line-height:1.55", "border-radius:4px;padding:10px 14px;font-size:.92em;line-height:1.55"),
    ("border-radius:8px;padding:10px 14px;font-size:.9em;color:#8b1a1a", "border-radius:4px;padding:10px 14px;font-size:.9em;color:#8b1a1a"),
    ("border-radius:12px;padding:14px 16px;", "border-radius:6px;padding:14px 16px;"),
]
for old, new in inline:
    if old in src:
        src = src.replace(old, new)
        print('inline replaced:', old[:55])
    else:
        print('inline NOT FOUND:', old[:60])

open('app.py', 'w', encoding='utf-8').write(src)
print('done. changed:', src != orig)
