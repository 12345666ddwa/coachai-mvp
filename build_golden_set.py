#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoachAI Golden Set 构建脚本
===========================
从 data/questions.json 的 18 道 2025 HSC Enterprise Computing 真题中，
选出 8 道「纯文本作答」的简答/论述题，每道生成 4 份不同质量档位的
模拟学生答案（excellent / good / weak / borderline），并依据官方
marking guidelines 人工推导期望分数与判分依据，输出 tests/golden_set.json。

选题目标准：
  * 排除纯选择题（ec2025-q11，checkbox）
  * 排除依赖下拉/表格交互的题（q15a dropdowns、q18 内嵌电子表格）
  * 排除依赖图片/绘图刺激材料的题（q19 UI 设计图、q21 DFD 绘图、
    q23a/q23b 数据看板图、q25 slideshow 刺激材料）
  * 保留纯文本刺激 + 文本作答的 describe/outline/explain/justify 题

质量档位定义（模拟真实学生，1-4 句话，含口语化/小错，非 AI 完美腔）：
  excellent : 依据官方 sample_answers 改写（换措辞不抄原文），可达满分
  good      : 方向正确、要点齐全但缺细节/例子/论证，通常低一档
  weak      : 只沾边或答非所问，0-1 分
  borderline: 故意模糊、介于相邻两档之间的边界情况

期望分数依据：每题官方 marking_guidelines 的 band 文字逐条比对推导，
note 中引用 criteria 关键词作为依据（NESA 不公布逐份给分，此分数为
CoachAI 团队按 MG 的推导值，非官方发布）。

用法:  python build_golden_set.py
输出:  tests/golden_set.json
"""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = BASE_DIR / "data" / "questions.json"
OUT_PATH = BASE_DIR / "tests" / "golden_set.json"

# 选中的 8 道题（全部为纯文本作答，无图片/交互依赖）
PICKED_IDS = [
    "ec2025-q14",   # 3 marks  memes 数据分析
    "ec2025-q16a",  # 4 marks  智能系统硬件/传感器
    "ec2025-q16b",  # 4 marks  专家系统 + Industry 4.0
    "ec2025-q17a",  # 3 marks  数据仓库收益
    "ec2025-q20",   # 3 marks  电子表格可视化功能
    "ec2025-q22a",  # 2 marks  项目管理工具
    "ec2025-q22b",  # 3 marks  数据安全方法 justify
    "ec2025-q24",   # 5 marks  freelance + offshore 优劣
]

QUALITY_ORDER = ["excellent", "good", "weak", "borderline"]

# --------------------------------------------------------------------------
# 每道题的 4 份答案。
# text : 学生答案原文（1-4 句，刻意口语化/带个别小错）
# quality : excellent | good | weak | borderline
# expected_marks : 依据官方 MG band 推导的期望分数（禁止拍脑袋，见 note）
# note : 判分依据，引用 marking_guidelines 的 criteria 关键词
# --------------------------------------------------------------------------
ANSWERS: dict[str, list[dict]] = {
    # ============================ q14 (3 marks) ============================
    "ec2025-q14": [
        {
            "quality": "excellent",
            "text": "Companies can look at how far and how fast a meme spreads, like counting shares, likes and reach, to gauge how engaged people are with the campaign. Data mining tools can then be used to pick out patterns and trends in the data, such as which memes took off and where. You can also analyse the theme and tone of the memes and comments to see whether the reaction to the ad is positive or negative.",
            "expected_marks": 3,
            "note": "band3（最高档）'Describes how memes can be analysed to provide insights into the effectiveness of the advertising campaign'——量化传播（频率/分享/触及）+ 数据挖掘找模式趋势 + 定性分析主题/态度，三路均展开（改写官方满分样例，未抄原文）。",
        },
        {
            "quality": "good",
            "text": "Memes could be analysed by checking how many people shared them, which shows how popular the campaign is. The comments would also give a rough idea of how people feel about the ad.",
            "expected_marks": 2,
            "note": "band2 'Outlines how memes can be analysed to provide insights into the effectiveness of the advertising campaign'——点出分享量与评论情绪两个方向，但未描述数据挖掘工具、模式/趋势分析等细节，深度未到 describe。",
        },
        {
            "quality": "weak",
            "text": "Memes are funny pictures that go viral on social media, and if everyone is sharing them then the advertising is obviously working. I saw a meme about this once, pretty sure memes help ads alot.",
            "expected_marks": 1,
            "note": "band1 'Provides some relevant information'——只有'传播广=广告有效'的直觉，后半句为无关内容，未描述任何分析方法。",
        },
        {
            "quality": "borderline",
            "text": "Memes can be counted and tracked to see how often they appear and how far they spread, which shows the campaign's viral impact. Data mining tools can identify patterns, trends and the reach of memes. The company could also look at the comments to see how people feel about the ad.",
            "expected_marks": 3,
            "note": "量化+数据挖掘两句接近官方满分样例，但'看评论'仅一句带过、未描述定性分析方法（主题/语气/态度）——处于 band2(outline) 与 band3(describe) 边界，判 3（从宽）；严格判分可落 2。",
        },
    ],
    # ============================ q16a (4 marks) ============================
    "ec2025-q16a": [
        {
            "quality": "excellent",
            "text": "The line would need sensors matched to each job, like cameras to visually check the LCD panel is attached properly, vibration sensors to detect problems with the machinery before a breakdown, and light sensors to measure the brightness of the screen during testing. All of these would connect back to the server over a network, so they'd also need networking hardware like switches, routers and ethernet cables or Wi-Fi to carry the live data.",
            "expected_marks": 4,
            "note": "band4（最高档）两条要求齐备：'Describes hardware needed for the intelligent system'（传感器分工 + 联网硬件 switch/router/传输介质）+ 'Includes examples of specific types of sensors'（camera/vibration/light 各有具体用途）。",
        },
        {
            "quality": "good",
            "text": "The factory would need to install sensors on the machines, like cameras and light sensors, and a network to send the collected data back to a server for processing.",
            "expected_marks": 3,
            "note": "band3 'Outlines relevant hardware devices; Includes at least ONE sensor'——列出传感器与网络但未描述具体作用/类型细节，未达 band4 的 describe 深度。",
        },
        {
            "quality": "weak",
            "text": "They need faster computers and more memory to handle all the data, and maybe some robots to do the boring jobs on the production line.",
            "expected_marks": 1,
            "note": "band1 'Provides some relevant information'——只谈通用计算设备与机器人，未涉及智能系统所需传感器/联网硬件，仅沾边。",
        },
        {
            "quality": "borderline",
            "text": "Sensors are the main hardware, like light sensors to test the brightness of each screen and vibration sensors to pick up faults in the machines early. These all have to be networked back to a central server so the data can be processed live, so the network setup matters as much as the sensors.",
            "expected_marks": 3,
            "note": "传感器有明确分工描述并点出网络必要性，但未点名 switch/router/server 等具体联网设备——band3(有传感器+outline 设备) 与 band4(describe 完整硬件) 之间，判 3。",
        },
    ],
    # ============================ q16b (4 marks) ============================
    "ec2025-q16b": [
        {
            "quality": "excellent",
            "text": "An expert system could analyse the sensor data and predict when maintenance is needed, so staff get warned before a machine fails and downtime is kept to a minimum. It could also inspect the TVs for defects more accurately than a human, catching subtle issues and stopping faulty screens from reaching the end of the line. This lines up with Industry 4.0, where smart factories use data to improve precision, reduce waste and lift product quality.",
            "expected_marks": 4,
            "note": "band4（最高档）'Explains potential benefits of introducing an expert system into the manufacturing process, with reference to Industry 4.0'——预测性维护与质检两个 benefit 均有因果解释，并落到 Industry 4.0 的 precision/waste/quality。",
        },
        {
            "quality": "good",
            "text": "An expert system would cut downtime because it can predict breakdowns before they happen, and it would also make quality control more consistent by checking every screen the same way.",
            "expected_marks": 3,
            "note": "band3 'Outlines potential benefits of introducing an expert system into the manufacturing process'——两个 benefit 方向正确，但未提及 Industry 4.0，缺最高档要求的呼应。",
        },
        {
            "quality": "weak",
            "text": "Expert systems are basically like having a super experienced worker who knows everything about the factory, so they should help out heaps.",
            "expected_marks": 1,
            "note": "band1 'Identifies potential benefits of introducing an expert system and/or features of Industry 4.0; Provides some relevant information'——只有'像老员工'的类比，无具体 benefit。",
        },
        {
            "quality": "borderline",
            "text": "It could analyse the live sensor data to predict when machines will fail, reducing downtime, and it can find defects in the screens more reliably than a person. This is all part of Industry 4.0 where factories become smarter and more automated.",
            "expected_marks": 3,
            "note": "benefit 解释充分，但 Industry 4.0 仅一句'更智能更自动化'的泛泛呼应，未扣 precision/waste/real-time 等特征——band3/band4 边界，判 3。",
        },
    ],
    # ============================ q17a (3 marks) ============================
    "ec2025-q17a": [
        {
            "quality": "excellent",
            "text": "A data warehouse lets the chain bring sales, geographic and demographic data from every branch into one central store, even though the data comes in different formats, and the cloud version can be scaled up as the volume grows. Because everything is in the one place, the marketing team can analyse it to find seasonal trends, like which drinks sell more in summer, and target promotions at the right branches.",
            "expected_marks": 3,
            "note": "band3（最高档）'Explains how the use of data warehousing could benefit the coffee shop chain'——多源整合 + 弹性扩展 + 具体业务收益（季节趋势→分店促销）因果链完整。",
        },
        {
            "quality": "good",
            "text": "It stores all the sales data from the different branches in one big central database, which makes it easier to run reports and see what is selling well.",
            "expected_marks": 2,
            "note": "band2 'Outlines how the use of data warehousing could benefit the coffee shop chain OR identifies features of data warehousing'——集中存储→方便报表属 outline，未解释为何/如何带来决策收益。",
        },
        {
            "quality": "weak",
            "text": "A data warehouse is basically a very large database that holds data from the whole business.",
            "expected_marks": 1,
            "note": "band1 'Identifies a feature of data warehousing'——只识别'集中大库'单一特征，无 benefit 内容。",
        },
        {
            "quality": "borderline",
            "text": "The chain can store all its sales and demographic data in the cloud so it won't run out of space as branches are added, and analysts can query the whole dataset at once instead of merging spreadsheets from every shop. This would make it faster to answer questions like which branch sells the most coffee.",
            "expected_marks": 2,
            "note": "前半为仓库特征（可扩展/统一查询）而非收益，收益只落到'查得快'一句，未形成业务决策收益链——band2/band3 边界（band3 需 explain how it benefits the chain），判 2。",
        },
    ],
    # ============================ q20 (3 marks) ============================
    "ec2025-q20": [
        {
            "quality": "excellent",
            "text": "Charts and graphs let the marine biologist turn raw data like water temperature into a picture, so she can see rising or falling trends over time and use them to predict how the fish population will change. Conditional formatting is also handy, because it can colour-code the cells, for example flagging low food availability or high pollution in red so the problem areas stand out straight away.",
            "expected_marks": 3,
            "note": "band3（最高档）'Describes spreadsheet features that can assist the marine biologist to better understand the datasets visually'——chart/graph 与 conditional formatting 均描述了可视化作用并扣合预测场景。",
        },
        {
            "quality": "good",
            "text": "She could use charts, like a line graph of water temperature over time, so the changes are much easier to see.",
            "expected_marks": 2,
            "note": "band2 'Outlines ONE spreadsheet feature that can assist the marine biologist to better understand the datasets visually OR identifies spreadsheet features'——只 outline 一个 chart，缺第二特征与场景细节。",
        },
        {
            "quality": "weak",
            "text": "Spreadsheets are a good way to organise all her data into rows and columns so it is in the one place, and she can sort it by date.",
            "expected_marks": 1,
            "note": "band1 'Provides some relevant information'——讲的是数据整理/排序而非可视化功能，仅沾边。",
        },
        {
            "quality": "borderline",
            "text": "A line chart of the water temperature against time would let her see straight away when temperatures spike, which helps explain sudden drops in the fish population. Pivot tables and conditional formatting could also be used to view the data differently.",
            "expected_marks": 3,
            "note": "chart 描述充分并扣预测场景；pivot/conditional formatting 只点名未描述——介于 band2（outline ONE feature / identify features）与 band3（describe features）之间，判 3（从宽）。",
        },
    ],
    # ============================ q22a (2 marks) ============================
    "ec2025-q22a": [
        {
            "quality": "excellent",
            "text": "A Gantt chart could be used to plan the project — it maps every task onto a timeline so the team can see what has to be done, when it's due and who is responsible, and they can track progress against the plan as the project goes.",
            "expected_marks": 2,
            "note": "band2（最高档）'Outlines a tool that can be used by the project team to manage the project'——任务、时间线、负责人、进度追踪多要素 outline。",
        },
        {
            "quality": "good",
            "text": "They could use a Gantt chart to plan the tasks.",
            "expected_marks": 1,
            "note": "band1 'Identifies a suitable tool or a feature of project management'——只识别合适工具（Gantt chart），无任何 outline 内容。",
        },
        {
            "quality": "weak",
            "text": "Maybe they should hire a dedicated project manager and have weekly catch-up meetings to keep everyone on track.",
            "expected_marks": 0,
            "note": "未识别任何工具（人员/会议不是工具），低于 band1 'Identifies a suitable tool' 的最低要求，给 0 分。",
        },
        {
            "quality": "borderline",
            "text": "A Gantt chart would help, it shows the tasks and when they need to be done by.",
            "expected_marks": 1,
            "note": "一句功能描述（显示任务+截止时间）介于 band1 'Identifies a suitable tool'（识别工具即止）与 band2 'Outlines a tool'（需 outline 其管理作用）之间，判 1。",
        },
    ],
    # ============================ q22b (3 marks) ============================
    "ec2025-q22b": [
        {
            "quality": "excellent",
            "text": "The company could give staff different access levels, so someone in claims only sees the claim files they need rather than all customer and employee records — that way an insider or a stolen login can't reach more data than necessary. They could also encrypt usernames and passwords when customers log in to the cloud server, so even if the transmission is intercepted the data can't be read.",
            "expected_marks": 3,
            "note": "band3（最高档）'Justifies TWO methods that the company can use to maintain the security of the data'——分级访问与加密传输两个方法各有 why/how 论证。",
        },
        {
            "quality": "good",
            "text": "Staff could have different access levels so they only see the data they need for their job, and the company could also encrypt the customer data. These are pretty standard security measures.",
            "expected_marks": 2,
            "note": "band2 'Outlines TWO methods that the company can use'——两方法 outline 齐全但无 justify 论证（'standard measures' 不构成论证）。",
        },
        {
            "quality": "weak",
            "text": "They should back up the data to a local server every night so it isn't lost if the cloud goes down.",
            "expected_marks": 1,
            "note": "band1 'Identifies ONE method that the company can use'——只识别 backup 一种方法。",
        },
        {
            "quality": "borderline",
            "text": "Different access levels mean an employee can only reach the records they need for their job, so if someone's account is compromised the damage is limited. The company should also encrypt the data when it's transmitted to customers.",
            "expected_marks": 2,
            "note": "方法一 justify 完整，方法二（加密）仅点名未论证 why——未达 band3 'Justifies TWO methods'，落 band2（outline 两法）；宽判可 3。",
        },
    ],
    # ============================ q24 (5 marks) ============================
    "ec2025-q24": [
        {
            "quality": "excellent",
            "text": "Offshore development gives the company access to a much bigger talent pool, including specialised design skills that are hard to find locally, and labour is often cheaper, which cuts the cost of the packaging design. But teams in other time zones and with different languages can slow feedback down and cause misunderstandings. Freelancers bring flexibility — the company can hire an expert for a single short-term design job without the overheads of a full team — although freelancers may not fully share the company's vision, so big projects can lose cohesion.",
            "expected_marks": 5,
            "note": "band5（最高档）'Explains advantages and disadvantages to the company in using freelance work and offshore development for packaging design'——两种模式各给出优势与劣势且均含因果解释（改写官方满分样例，未抄原文）。",
        },
        {
            "quality": "good",
            "text": "Offshore development is cheaper and gives access to skilled people overseas, but time zone differences can slow down communication. Freelancers can be hired for specific jobs so the company doesn't need a full design team, though they might not be as aligned with the company's brand.",
            "expected_marks": 4,
            "note": "band4 'Outlines advantages and disadvantages to the company in using freelance work and offshore development for packaging design'——双方优劣要素齐备但均为 outline，无 explain 深度。",
        },
        {
            "quality": "weak",
            "text": "Freelancers probably enjoy working from home in their own hours, and offshore teams are in countries like India so they can work while we sleep and the project never really stops.",
            "expected_marks": 1,
            "note": "band1 'Provides some relevant information'——从员工/时区视角给模糊描述，未形成对公司使用两种方式的优劣势分析（'永不停止'判断亦失准）。",
        },
        {
            "quality": "borderline",
            "text": "Offshore development can cut the cost of the design work because wages are lower in other countries, but communication gets harder across time zones and feedback takes longer. Freelancers would also give the company flexibility to bring in designers only when a packaging project comes up.",
            "expected_marks": 3,
            "note": "offshore 优劣有 outline/部分 explain，freelance 只覆盖优势一方——介于 band3 'Outlines some features of freelance work and/or offshore development' 与 band4（需 outline 两模式各自优劣）之间，判 3。",
        },
    ],
}


def main() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))["questions"]
    by_id = {q["id"]: q for q in questions}

    # 校验：题目存在、marks 一致、答案四档齐全
    missing = [qid for qid in PICKED_IDS if qid not in by_id]
    if missing:
        raise SystemExit(f"[build_golden_set] 题目不存在于 questions.json: {missing}")
    for qid in PICKED_IDS:
        q = by_id[qid]
        ans = ANSWERS[qid]
        if len(ans) != 4 or {a["quality"] for a in ans} != set(QUALITY_ORDER):
            raise SystemExit(f"[build_golden_set] {qid} 答案档位不齐: "
                             f"{[a['quality'] for a in ans]}")
        for a in ans:
            if not (0 <= a["expected_marks"] <= q["marks"]):
                raise SystemExit(
                    f"[build_golden_set] {qid}/{a['quality']} 期望分数 "
                    f"{a['expected_marks']} 超出 [0, {q['marks']}]")
            if not a["text"].strip() or not a["note"].strip():
                raise SystemExit(f"[build_golden_set] {qid}/{a['quality']} 空文本")

    items = []
    for qid in PICKED_IDS:
        q = by_id[qid]
        items.append({
            "question_id": qid,
            "question_text": q["text"],
            "marks": q["marks"],
            "answers": [
                {
                    "text": a["text"],
                    "quality": a["quality"],
                    "expected_marks": a["expected_marks"],
                    "note": a["note"],
                }
                for a in ANSWERS[qid]
            ],
        })

    golden = {
        "generated_by": "CoachAI build_golden_set.py — 8 道 2025 HSC Enterprise Computing 真题 × 4 质量档；"
                        "期望分数由 CoachAI 团队逐条对照官方 marking guidelines 的 band 文字人工推导，"
                        "非 NESA 官方发布的逐份分数（NESA 不公布）。",
        "based_on": "2025 HSC Enterprise Computing — official NESA paper & marking guidelines "
                    "(data/questions.json 收录自 raw/mg2025.pdf) 及官方 full-mark samples (raw/samples2025.pdf)",
        "note": "每题 4 档：excellent（满分/接近满分）/ good（正确但缺细节，低一档）/ "
                "weak（仅沾边，0-1 分）/ borderline（故意模糊，介于两档之间）。"
                "答案刻意口语化、1-4 句话，模拟真实学生作答。",
        "items": items,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(golden, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    # 汇总打印
    n_answers = sum(len(i["answers"]) for i in items)
    print(f"[build_golden_set] 已生成 {OUT_PATH}")
    print(f"  题目数: {len(items)}  ({', '.join(i['question_id'] for i in items)})")
    print(f"  答案总数: {n_answers}")
    print("  期望分数分布 (expected_marks):")
    dist: dict[int, int] = {}
    for i in items:
        for a in i["answers"]:
            dist[a["expected_marks"]] = dist.get(a["expected_marks"], 0) + 1
    for m in sorted(dist):
        print(f"    {m} 分 × {dist[m]}")
    print("  每档期望分数:",
          {q: [a['expected_marks'] for i in items for a in i['answers'] if a['quality'] == q]
           for q in QUALITY_ORDER})


if __name__ == "__main__":
    main()
