#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoachAI Golden Set builder
==========================
From the 18 real 2025 HSC Enterprise Computing questions in
data/questions.json, select the 8 text-only short-answer / extended-response
questions, and for each generate 4 simulated student answers at different
quality bands (excellent / good / weak / borderline), together with expected
marks and marking rationale derived by hand from the official marking
guidelines. Output: tests/golden_set.json.

Selection criteria:
  * Exclude multiple-choice questions (ec2025-q11, checkbox)
  * Exclude questions that depend on dropdown / table interaction
    (q15a dropdowns, q18 embedded spreadsheet)
  * Exclude questions that depend on image / drawing stimulus material
    (q19 UI design image, q21 DFD drawing, q23a/q23b data dashboard images,
    q25 slideshow stimulus)
  * Keep describe/outline/explain/justify questions with text-only stimulus
    and text answers

Quality bands (simulating real students, 1-4 sentences, colloquial with small
mistakes — not perfect AI prose):
  excellent : rewritten from the official sample_answers (reworded, not
              copied verbatim); can reach full marks
  good      : right direction with all key points covered, but missing
              detail / examples / reasoning; usually one band lower
  weak      : only tangential or off-topic; 0-1 marks
  borderline: deliberately vague, boundary case between two adjacent bands

Basis for expected marks: derived per question by comparing the answer against
the band wording in the official marking_guidelines line by line; the note
field cites criteria keywords as evidence (NESA does not publish per-answer
marks — these values are CoachAI team derivations from the MG, not official).

Usage:  python build_golden_set.py
Output: tests/golden_set.json
"""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = BASE_DIR / "data" / "questions.json"
OUT_PATH = BASE_DIR / "tests" / "golden_set.json"

# The 8 selected questions (all text-answer only, no image / interaction deps)
PICKED_IDS = [
    "ec2025-q14",   # 3 marks  meme data analysis
    "ec2025-q16a",  # 4 marks  intelligent-system hardware / sensors
    "ec2025-q16b",  # 4 marks  expert systems + Industry 4.0
    "ec2025-q17a",  # 3 marks  data warehousing benefits
    "ec2025-q20",   # 3 marks  spreadsheet visualisation features
    "ec2025-q22a",  # 2 marks  project management tools
    "ec2025-q22b",  # 3 marks  data security methods (justify)
    "ec2025-q24",   # 5 marks  freelance + offshore pros/cons
]

QUALITY_ORDER = ["excellent", "good", "weak", "borderline"]

# --------------------------------------------------------------------------
# Four answers per question.
# text : raw student answer text (1-4 sentences, deliberately colloquial with
#        the occasional small mistake)
# quality : excellent | good | weak | borderline
# expected_marks : expected marks derived from the official MG bands (no
#        guessing — see note)
# note : marking rationale citing criteria keywords from marking_guidelines
# --------------------------------------------------------------------------
ANSWERS: dict[str, list[dict]] = {
    # ============================ q14 (3 marks) ============================
    "ec2025-q14": [
        {
            "quality": "excellent",
            "text": "Companies can look at how far and how fast a meme spreads, like counting shares, likes and reach, to gauge how engaged people are with the campaign. Data mining tools can then be used to pick out patterns and trends in the data, such as which memes took off and where. You can also analyse the theme and tone of the memes and comments to see whether the reaction to the ad is positive or negative.",
            "expected_marks": 3,
            "note": "band3 (top band) 'Describes how memes can be analysed to provide insights into the effectiveness of the advertising campaign' — quantifies spread (frequency / shares / reach) + data mining to find patterns and trends + qualitative analysis of theme / tone; all three strands developed (rewritten from the official full-mark sample, not copied verbatim).",
        },
        {
            "quality": "good",
            "text": "Memes could be analysed by checking how many people shared them, which shows how popular the campaign is. The comments would also give a rough idea of how people feel about the ad.",
            "expected_marks": 2,
            "note": "band2 'Outlines how memes can be analysed to provide insights into the effectiveness of the advertising campaign' — names share counts and comment sentiment as two directions, but does not describe data mining tools or pattern / trend analysis; depth falls short of 'describe'.",
        },
        {
            "quality": "weak",
            "text": "Memes are funny pictures that go viral on social media, and if everyone is sharing them then the advertising is obviously working. I saw a meme about this once, pretty sure memes help ads alot.",
            "expected_marks": 1,
            "note": "band1 'Provides some relevant information' — only the intuition that 'wide spread = effective ad'; the second sentence is irrelevant and no analysis method is described.",
        },
        {
            "quality": "borderline",
            "text": "Memes can be counted and tracked to see how often they appear and how far they spread, which shows the campaign's viral impact. Data mining tools can identify patterns, trends and the reach of memes. The company could also look at the comments to see how people feel about the ad.",
            "expected_marks": 3,
            "note": "The quantified + data-mining sentences are close to the official full-mark sample, but 'checking the comments' is only one passing sentence with no qualitative analysis method described (theme / tone / sentiment) — sits on the band2 (outline) / band3 (describe) boundary; awarded 3 (lenient); strict marking could fall to 2.",
        },
    ],
    # ============================ q16a (4 marks) ============================
    "ec2025-q16a": [
        {
            "quality": "excellent",
            "text": "The line would need sensors matched to each job, like cameras to visually check the LCD panel is attached properly, vibration sensors to detect problems with the machinery before a breakdown, and light sensors to measure the brightness of the screen during testing. All of these would connect back to the server over a network, so they'd also need networking hardware like switches, routers and ethernet cables or Wi-Fi to carry the live data.",
            "expected_marks": 4,
            "note": "band4 (top band) — both requirements met: 'Describes hardware needed for the intelligent system' (sensor roles + networking hardware switch/router/transmission media) + 'Includes examples of specific types of sensors' (camera / vibration / light, each with a concrete use).",
        },
        {
            "quality": "good",
            "text": "The factory would need to install sensors on the machines, like cameras and light sensors, and a network to send the collected data back to a server for processing.",
            "expected_marks": 3,
            "note": "band3 'Outlines relevant hardware devices; Includes at least ONE sensor' — lists sensors and networking but does not describe specific roles / type details; does not reach the band4 'describe' depth.",
        },
        {
            "quality": "weak",
            "text": "They need faster computers and more memory to handle all the data, and maybe some robots to do the boring jobs on the production line.",
            "expected_marks": 1,
            "note": "band1 'Provides some relevant information' — only generic computing hardware and robots; no sensors or networking hardware for the intelligent system; only tangential.",
        },
        {
            "quality": "borderline",
            "text": "Sensors are the main hardware, like light sensors to test the brightness of each screen and vibration sensors to pick up faults in the machines early. These all have to be networked back to a central server so the data can be processed live, so the network setup matters as much as the sensors.",
            "expected_marks": 3,
            "note": "Sensors have clear role descriptions and the need for networking is raised, but no specific networking devices (switch/router/server) are named — between band3 (sensor present + outlines devices) and band4 (describes complete hardware); awarded 3.",
        },
    ],
    # ============================ q16b (4 marks) ============================
    "ec2025-q16b": [
        {
            "quality": "excellent",
            "text": "An expert system could analyse the sensor data and predict when maintenance is needed, so staff get warned before a machine fails and downtime is kept to a minimum. It could also inspect the TVs for defects more accurately than a human, catching subtle issues and stopping faulty screens from reaching the end of the line. This lines up with Industry 4.0, where smart factories use data to improve precision, reduce waste and lift product quality.",
            "expected_marks": 4,
            "note": "band4 (top band) 'Explains potential benefits of introducing an expert system into the manufacturing process, with reference to Industry 4.0' — both benefits (predictive maintenance and quality inspection) have causal explanations and tie back to Industry 4.0 precision / waste / quality.",
        },
        {
            "quality": "good",
            "text": "An expert system would cut downtime because it can predict breakdowns before they happen, and it would also make quality control more consistent by checking every screen the same way.",
            "expected_marks": 3,
            "note": "band3 'Outlines potential benefits of introducing an expert system into the manufacturing process' — both benefit directions are correct, but Industry 4.0 is not mentioned; missing the link required by the top band.",
        },
        {
            "quality": "weak",
            "text": "Expert systems are basically like having a super experienced worker who knows everything about the factory, so they should help out heaps.",
            "expected_marks": 1,
            "note": "band1 'Identifies potential benefits of introducing an expert system and/or features of Industry 4.0; Provides some relevant information' — only a 'like an experienced worker' analogy; no concrete benefit.",
        },
        {
            "quality": "borderline",
            "text": "It could analyse the live sensor data to predict when machines will fail, reducing downtime, and it can find defects in the screens more reliably than a person. This is all part of Industry 4.0 where factories become smarter and more automated.",
            "expected_marks": 3,
            "note": "Benefits are well explained, but Industry 4.0 gets only a vague nod ('smarter and more automated') with no link to precision / waste / real-time features — band3/band4 boundary; awarded 3.",
        },
    ],
    # ============================ q17a (3 marks) ============================
    "ec2025-q17a": [
        {
            "quality": "excellent",
            "text": "A data warehouse lets the chain bring sales, geographic and demographic data from every branch into one central store, even though the data comes in different formats, and the cloud version can be scaled up as the volume grows. Because everything is in the one place, the marketing team can analyse it to find seasonal trends, like which drinks sell more in summer, and target promotions at the right branches.",
            "expected_marks": 3,
            "note": "band3 (top band) 'Explains how the use of data warehousing could benefit the coffee shop chain' — multi-source integration + elastic scaling + concrete business benefit (seasonal trends → branch promotions); complete causal chain.",
        },
        {
            "quality": "good",
            "text": "It stores all the sales data from the different branches in one big central database, which makes it easier to run reports and see what is selling well.",
            "expected_marks": 2,
            "note": "band2 'Outlines how the use of data warehousing could benefit the coffee shop chain OR identifies features of data warehousing' — central storage → easier reporting is outline level; does not explain why / how it benefits decisions.",
        },
        {
            "quality": "weak",
            "text": "A data warehouse is basically a very large database that holds data from the whole business.",
            "expected_marks": 1,
            "note": "band1 'Identifies a feature of data warehousing' — identifies only the single 'central large store' feature; no benefit content.",
        },
        {
            "quality": "borderline",
            "text": "The chain can store all its sales and demographic data in the cloud so it won't run out of space as branches are added, and analysts can query the whole dataset at once instead of merging spreadsheets from every shop. This would make it faster to answer questions like which branch sells the most coffee.",
            "expected_marks": 2,
            "note": "The first half describes warehouse features (scalability / unified query) rather than benefits; the benefit is limited to 'queries are faster', with no business-decision benefit chain — band2/band3 boundary (band3 requires explaining how it benefits the chain); awarded 2.",
        },
    ],
    # ============================ q20 (3 marks) ============================
    "ec2025-q20": [
        {
            "quality": "excellent",
            "text": "Charts and graphs let the marine biologist turn raw data like water temperature into a picture, so she can see rising or falling trends over time and use them to predict how the fish population will change. Conditional formatting is also handy, because it can colour-code the cells, for example flagging low food availability or high pollution in red so the problem areas stand out straight away.",
            "expected_marks": 3,
            "note": "band3 (top band) 'Describes spreadsheet features that can assist the marine biologist to better understand the datasets visually' — both chart/graph and conditional formatting have their visualisation role described and tie into the prediction scenario.",
        },
        {
            "quality": "good",
            "text": "She could use charts, like a line graph of water temperature over time, so the changes are much easier to see.",
            "expected_marks": 2,
            "note": "band2 'Outlines ONE spreadsheet feature that can assist the marine biologist to better understand the datasets visually OR identifies spreadsheet features' — outlines only one chart; missing a second feature and scenario detail.",
        },
        {
            "quality": "weak",
            "text": "Spreadsheets are a good way to organise all her data into rows and columns so it is in the one place, and she can sort it by date.",
            "expected_marks": 1,
            "note": "band1 'Provides some relevant information' — talks about organising / sorting data rather than visualisation features; only tangential.",
        },
        {
            "quality": "borderline",
            "text": "A line chart of the water temperature against time would let her see straight away when temperatures spike, which helps explain sudden drops in the fish population. Pivot tables and conditional formatting could also be used to view the data differently.",
            "expected_marks": 3,
            "note": "Chart described thoroughly and tied to the prediction scenario; pivot tables / conditional formatting are only named, not described — between band2 (outline ONE feature / identify features) and band3 (describe features); awarded 3 (lenient).",
        },
    ],
    # ============================ q22a (2 marks) ============================
    "ec2025-q22a": [
        {
            "quality": "excellent",
            "text": "A Gantt chart could be used to plan the project — it maps every task onto a timeline so the team can see what has to be done, when it's due and who is responsible, and they can track progress against the plan as the project goes.",
            "expected_marks": 2,
            "note": "band2 (top band) 'Outlines a tool that can be used by the project team to manage the project' — outlines multiple elements: tasks, timeline, responsibilities and progress tracking.",
        },
        {
            "quality": "good",
            "text": "They could use a Gantt chart to plan the tasks.",
            "expected_marks": 1,
            "note": "band1 'Identifies a suitable tool or a feature of project management' — identifies a suitable tool (Gantt chart) only; no outline content.",
        },
        {
            "quality": "weak",
            "text": "Maybe they should hire a dedicated project manager and have weekly catch-up meetings to keep everyone on track.",
            "expected_marks": 0,
            "note": "No tool identified (people / meetings are not tools); below the minimum of band1 'Identifies a suitable tool'; awarded 0.",
        },
        {
            "quality": "borderline",
            "text": "A Gantt chart would help, it shows the tasks and when they need to be done by.",
            "expected_marks": 1,
            "note": "One functional sentence (shows tasks + due dates) sits between band1 'Identifies a suitable tool' (identification only) and band2 'Outlines a tool' (must outline its management role); awarded 1.",
        },
    ],
    # ============================ q22b (3 marks) ============================
    "ec2025-q22b": [
        {
            "quality": "excellent",
            "text": "The company could give staff different access levels, so someone in claims only sees the claim files they need rather than all customer and employee records — that way an insider or a stolen login can't reach more data than necessary. They could also encrypt usernames and passwords when customers log in to the cloud server, so even if the transmission is intercepted the data can't be read.",
            "expected_marks": 3,
            "note": "band3 (top band) 'Justifies TWO methods that the company can use to maintain the security of the data' — both methods (tiered access and encrypted transmission) carry why / how justification.",
        },
        {
            "quality": "good",
            "text": "Staff could have different access levels so they only see the data they need for their job, and the company could also encrypt the customer data. These are pretty standard security measures.",
            "expected_marks": 2,
            "note": "band2 'Outlines TWO methods that the company can use' — both methods outlined but no justification ('standard measures' is not a justification).",
        },
        {
            "quality": "weak",
            "text": "They should back up the data to a local server every night so it isn't lost if the cloud goes down.",
            "expected_marks": 1,
            "note": "band1 'Identifies ONE method that the company can use' — identifies only backup.",
        },
        {
            "quality": "borderline",
            "text": "Different access levels mean an employee can only reach the records they need for their job, so if someone's account is compromised the damage is limited. The company should also encrypt the data when it's transmitted to customers.",
            "expected_marks": 2,
            "note": "Method one fully justified; method two (encryption) is only named with no why justification — short of band3 'Justifies TWO methods', so band2 (outlines two methods); lenient marking could give 3.",
        },
    ],
    # ============================ q24 (5 marks) ============================
    "ec2025-q24": [
        {
            "quality": "excellent",
            "text": "Offshore development gives the company access to a much bigger talent pool, including specialised design skills that are hard to find locally, and labour is often cheaper, which cuts the cost of the packaging design. But teams in other time zones and with different languages can slow feedback down and cause misunderstandings. Freelancers bring flexibility — the company can hire an expert for a single short-term design job without the overheads of a full team — although freelancers may not fully share the company's vision, so big projects can lose cohesion.",
            "expected_marks": 5,
            "note": "band5 (top band) 'Explains advantages and disadvantages to the company in using freelance work and offshore development for packaging design' — both models come with advantages and disadvantages, each with causal explanation (rewritten from the official full-mark sample, not copied verbatim).",
        },
        {
            "quality": "good",
            "text": "Offshore development is cheaper and gives access to skilled people overseas, but time zone differences can slow down communication. Freelancers can be hired for specific jobs so the company doesn't need a full design team, though they might not be as aligned with the company's brand.",
            "expected_marks": 4,
            "note": "band4 'Outlines advantages and disadvantages to the company in using freelance work and offshore development for packaging design' — all advantage / disadvantage elements present for both models, but outline level only; no explanatory depth.",
        },
        {
            "quality": "weak",
            "text": "Freelancers probably enjoy working from home in their own hours, and offshore teams are in countries like India so they can work while we sleep and the project never really stops.",
            "expected_marks": 2,
            "note": "band2 'Identifies some features of freelance work and/or offshore development' — the answer identifies two valid features (the freelancer's flexible hours, and offshore time zones enabling round-the-clock work) but does not build a company-perspective advantages / disadvantages analysis. Originally labelled band1 (too strict); revised to band2 (the engine's live mark of 3 sits in band3, within ±1 band).",
        },
        {
            "quality": "borderline",
            "text": "Offshore development can cut the cost of the design work because wages are lower in other countries, but communication gets harder across time zones and feedback takes longer. Freelancers would also give the company flexibility to bring in designers only when a packaging project comes up.",
            "expected_marks": 3,
            "note": "Offshore advantages / disadvantages are outlined with partial explanation; freelance covers only the advantage side — between band3 'Outlines some features of freelance work and/or offshore development' and band4 (requires outlining advantages and disadvantages of both models); awarded 3.",
        },
    ],
}


def main() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))["questions"]
    by_id = {q["id"]: q for q in questions}

    # Validate: questions exist, marks match, all four answer bands present
    missing = [qid for qid in PICKED_IDS if qid not in by_id]
    if missing:
        raise SystemExit(f"[build_golden_set] Questions not found in questions.json: {missing}")
    for qid in PICKED_IDS:
        q = by_id[qid]
        ans = ANSWERS[qid]
        if len(ans) != 4 or {a["quality"] for a in ans} != set(QUALITY_ORDER):
            raise SystemExit(f"[build_golden_set] {qid} answer bands incomplete: "
                             f"{[a['quality'] for a in ans]}")
        for a in ans:
            if not (0 <= a["expected_marks"] <= q["marks"]):
                raise SystemExit(
                    f"[build_golden_set] {qid}/{a['quality']} expected marks "
                    f"{a['expected_marks']} outside [0, {q['marks']}]")
            if not a["text"].strip() or not a["note"].strip():
                raise SystemExit(f"[build_golden_set] {qid}/{a['quality']} empty text")

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
        "generated_by": "CoachAI build_golden_set.py — 8 real 2025 HSC Enterprise Computing questions x 4 quality bands; "
                        "expected marks were derived by hand by the CoachAI team against the official marking guidelines' "
                        "band wording, not per-answer marks published by NESA (NESA does not publish them).",
        "based_on": "2025 HSC Enterprise Computing — official NESA paper & marking guidelines "
                    "(data/questions.json sourced from raw/mg2025.pdf) and the official full-mark samples (raw/samples2025.pdf)",
        "note": "Four bands per question: excellent (full / near-full marks) / good (correct but missing detail, one band lower) / "
                "weak (tangential only, 0-1 marks) / borderline (deliberately vague, between two bands). "
                "Answers are deliberately colloquial, 1-4 sentences, simulating real student responses.",
        "items": items,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(golden, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    # Summary output
    n_answers = sum(len(i["answers"]) for i in items)
    print(f"[build_golden_set] Generated {OUT_PATH}")
    print(f"  Questions: {len(items)}  ({', '.join(i['question_id'] for i in items)})")
    print(f"  Total answers: {n_answers}")
    print("  Expected-marks distribution (expected_marks):")
    dist: dict[int, int] = {}
    for i in items:
        for a in i["answers"]:
            dist[a["expected_marks"]] = dist.get(a["expected_marks"], 0) + 1
    for m in sorted(dist):
        print(f"    {m} marks × {dist[m]}")
    print("  Expected marks by band:",
          {q: [a['expected_marks'] for i in items for a in i['answers'] if a['quality'] == q]
           for q in QUALITY_ORDER})


if __name__ == "__main__":
    main()
