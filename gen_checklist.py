#!/usr/bin/env python3
"""Generate the human-readable syllabus checklist for the lesson planner."""
import json

d = json.load(open('/home/gaogao/workspace/ai-coach/data/syllabus.json', encoding='utf-8'))

lines = []
lines.append('# Enterprise Computing Syllabus Checklist')
lines.append('**Source: NSW Enterprise Computing 11-12 Syllabus (2022), NESA official digital syllabus**')
lines.append('Extracted for the lesson-planner topic picker. Teachers tick the syllabus dot points they want covered;')
lines.append('the AI generates a lesson plan around the selection.')
lines.append('')
lines.append('Extraction notes: pulled from curriculum.nsw.edu.au (official digital syllabus pages), filtered to the')
lines.append('mainstream Enterprise Computing syllabus (Life Skills variants excluded). Total: 180 content points')
lines.append('across 7 focus areas, plus 22 outcomes.')
lines.append('')
lines.append('---')
lines.append('')

for year in ['Year 11', 'Year 12']:
    lines.append(f'# {year}')
    lines.append('')
    for m in d[year]['modules']:
        lines.append(f"## {m['focus_area']}")
        lines.append('')
        for g in m['content_groups']:
            lines.append(f"### {g['title']}")
            lines.append('')
            for dp in g['dot_points']:
                lines.append(f"- [ ] {dp['text']}")
            lines.append('')
    # outcomes for this year
    outs = [o for o in d['all_outcomes'] if f"-{year[-2:]}-" in o['code']]
    if outs:
        lines.append(f'## {year} outcomes (EC-{year[-2:]}-XX)')
        lines.append('')
        for o in outs:
            lines.append(f"- **{o['code']}** - {o['text']}")
        lines.append('')
    lines.append('---')
    lines.append('')

with open('/home/gaogao/workspace/ai-coach/docs/SYLLABUS_CHECKLIST.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print('saved docs/SYLLABUS_CHECKLIST.md')
print('lines:', len(lines))
