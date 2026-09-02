#!/usr/bin/env python3
"""CoachAI report figures v2 - layout-corrected.
Rules: arrows start/end exactly on box edges; layer labels get dedicated space;
text lines are width-checked against box width; legend outside data area.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

BLUE = "#1F4E79"
BLUE_SOFT = "#DCE6F1"
ORANGE = "#E69F00"
ORANGE_SOFT = "#FDEBD0"
GREEN = "#2E7D32"
GREEN_SOFT = "#E2EFDA"
RED = "#C62828"
RED_SOFT = "#FADBD8"
GRAY = "#8C97A3"
INK = "#1A2332"
PAPER = "#FFFFFF"

OUT = "/home/gaogao/workspace/ai-coach/docs/figures"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": PAPER,
                     "axes.facecolor": PAPER, "axes.edgecolor": "#CCCCCC"})

def est_chars(box_w_units, fig_w_in, fs):
    """Max chars per line that fit in a box (conservative: char width ~0.55*fs)."""
    pt_w = box_w_units / 100.0 * fig_w_in * 72.0
    return int(pt_w / (0.55 * fs)) - 1

def fit_lines(text, box_w_units, fig_w_in, fs):
    """Return text broken into lines that fit (manual wrapping)."""
    cap = est_chars(box_w_units, fig_w_in, fs)
    out = []
    for line in text.split("\n"):
        while len(line) > cap:
            cut = line.rfind(" ", 0, cap)
            if cut < cap * 0.5:
                cut = cap
            out.append(line[:cut].strip())
            line = line[cut:].strip()
        out.append(line)
    return out

def box(ax, x, y, w, h, text, fig_w_in, fc=BLUE_SOFT, ec=BLUE, tc=INK, fs=9.5,
        bold=False, lh=3.6):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                       linewidth=1.3, facecolor=fc, edgecolor=ec, zorder=3)
    ax.add_patch(p)
    lines = fit_lines(text, w, fig_w_in, fs)
    n = len(lines)
    # start slightly above vertical center so multi-line text sits centered
    start_y = y + h / 2 + (n - 1) * lh / 2
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, start_y - i * lh, ln, ha="center", va="center",
                fontsize=fs, color=tc, zorder=4,
                fontweight="bold" if bold else "normal")
    return p

def arrow(ax, x1, y1, x2, y2, color=GRAY, lw=1.7, label=None):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14,
                        linewidth=lw, color=color, zorder=2)
    ax.add_patch(a)
    if label:
        ax.text((x1 + x2) / 2 + 0.7, (y1 + y2) / 2 + 0.8, label, fontsize=8,
                color=color, ha="left", va="bottom", zorder=5)

def new_ax(w_in, h_in, title=None, subtitle=None):
    fig, ax = plt.subplots(figsize=(w_in, h_in))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    if title:
        ax.text(0, 100.5, title, fontsize=13, fontweight="bold", color=INK, va="top")
    if subtitle:
        ax.text(0, 98.0, subtitle, fontsize=9.5, color=GRAY, va="top")
    return fig, ax

# ================================================================ 1. ARCHITECTURE
W = 10.4
fig, ax = new_ax(W, 6.6,
    "CoachAI System Architecture",
    "NESA material is the single source of truth; all model calls go through one abstraction layer")

def layer_label(ax, x, y, text, color=GRAY):
    ax.text(x, y, text, fontsize=8, fontweight="bold", color=color, ha="left", va="center")

# --- DATA layer (bottom) y 4..14, label band y 11.5..14
layer_label(ax, 2, 12.6, "DATA LAYER")
box(ax, 4, 5, 40, 6.5, "NESA official materials\nsyllabus + 4x TSR modules", W, fc="#F2F4F7", ec="#B9C2CC", fs=8.8)
box(ax, 56, 5, 40, 6.5, "Question bank\n18 questions + official\nmarking guidelines (2025 HSC)", W, fc="#F2F4F7", ec="#B9C2CC", fs=8.8)
# RAG index box in between
box(ax, 47.5, 4.6, 5, 7, "", W, fc="none", ec="none", fs=8)
ax.text(50, 8.2, "index", fontsize=7.5, color=GRAY, ha="center")

# --- Graph layer y 19..33, label band top
layer_label(ax, 2, 31.2, "LANGGRAPH LAYER", "#B26A00")
box(ax, 4, 20.5, 42, 8.5, "Graph A: mark_graph\nshort-answer marking\n(active)", W, fc=ORANGE_SOFT, ec=ORANGE, fs=9)
box(ax, 54, 20.5, 42, 8.5, "Graph B: report_graph\nreport feedback\n(next phase)", W, fc=ORANGE_SOFT, ec=ORANGE, tc=GRAY, fs=9)

# --- Agent layer y 39..55, label band top
layer_label(ax, 2, 53.2, "AGENT LAYER", BLUE)
box(ax, 4, 40.5, 42, 10.5, "Marker Agent  (T=0.5)\nHSC teacher: provisional marks\n+ feedback", W, fc=BLUE_SOFT, ec=BLUE, fs=9)
box(ax, 54, 40.5, 42, 10.5, "Verifier Agent  (T=0.2)\nQA auditor: recompute mark, flags,\nconfidence, refine feedback", W, fc=BLUE_SOFT, ec=BLUE, fs=9)

# --- Service layer y 61..71, label band top
layer_label(ax, 2, 69.2, "SERVICE LAYER", GREEN)
box(ax, 26, 62, 48, 6.5, "Gradio UI - phone-friendly web demo (EN/CN)", W, fc=GREEN_SOFT, ec=GREEN, fs=9)

# --- Model rail (right side) y 20..73
box(ax, 88, 20, 11, 53, "", W, fc="#FBF0F0", ec="#E3B7B7")
ax.text(89.3, 70.8, "MODEL\nABSTRACTION", fontsize=7.6, fontweight="bold", color=RED,
        ha="left", va="top")
box(ax, 89.2, 59, 8.6, 8, "deepseek\nv4-flash\n(now)", W, fc=RED_SOFT, ec=RED, fs=7.6)
box(ax, 89.2, 47, 8.6, 8, "gemini\n3.5 flash\n(free)", W, fc=RED_SOFT, ec=RED, tc=GRAY, fs=7.6)
box(ax, 89.2, 35, 8.6, 8, "ollama\n(local)", W, fc=RED_SOFT, ec=RED, tc=GRAY, fs=7.6)
box(ax, 89.2, 23.5, 8.6, 7, "swap = 1\nconfig\nline", W, fc="#FFFFFF", ec=RED, tc=RED, fs=7.2)

# --- Arrows: strictly edge to edge
# data -> graph (up, both lanes)
arrow(ax, 24, 11.5, 24, 19.2, color=GRAY, lw=1.6)
arrow(ax, 76, 11.5, 76, 19.2, color=GRAY, lw=1.6)
# graph -> agent
arrow(ax, 24, 29, 24, 39.2, color=BLUE, lw=1.6)
arrow(ax, 76, 29, 76, 39.2, color=BLUE, lw=1.6)
# agent -> service
arrow(ax, 48, 51, 48, 60.8, color=GREEN, lw=1.7)
# service -> model rail? no: model rail is accessed by agents, draw from rail to agents
arrow(ax, 93, 66.8, 93, 62, color=RED, lw=0)   # invisible placeholder (kept out)
# agents -> model rail (call direction): from agent layer right edge to rail left edge
arrow(ax, 96.5, 45.5, 99.3, 45.5, color=RED, lw=1.2)
# RAG retriever note (left side, inside graph band gap is occupied - put under graph A)
box(ax, 4, 33.4, 42, 4.4, "RAG retriever: search(query) -> top-k syllabus chunks", W,
    fc="#FFFFFF", ec="#C9D3DE", fs=8)
arrow(ax, 25, 37.8, 25, 40.2, color=ORANGE, lw=1.4)

fig.savefig(f"{OUT}/architecture.png", dpi=200, bbox_inches="tight", facecolor=PAPER)
plt.close(fig)
print("OK architecture v2")

# ================================================================ 2. WORKFLOW 1
W = 10.0
fig, ax = new_ax(W, 7.4,
    "Workflow 1: Short-Answer Marking (LangGraph State Machine)",
    "RAG before grading; Verifier audits every verdict; retries capped at 2; never raises")

CX = 50  # central column x center
BW = 24  # box width

def center_box(y, h, text, fc, ec, fs=9.2, bold=False, tc=INK):
    box(ax, CX - BW / 2, y, BW, h, text, W, fc=fc, ec=ec, fs=fs, bold=bold, tc=tc)

# input
center_box(93, 4.6, "INPUT\nquestion_id + student answer", "#F2F4F7", "#B9C2CC", fs=8.6)
arrow(ax, CX, 93, CX, 90.2, lw=1.5)
# load
center_box(84.5, 5.7, "load_question\npull question + official\nmarking guidelines", BLUE_SOFT, BLUE, fs=8.8)
arrow(ax, CX, 84.5, CX, 81.8, lw=1.5)
# retrieve
center_box(75.5, 6.3, "retrieve (RAG)\n4 syllabus chunks\ninjected into prompt", ORANGE_SOFT, ORANGE, fs=8.8)
arrow(ax, CX, 75.5, CX, 72.6, lw=1.5)
# grade
center_box(66, 6.6, "grade (Marker, T=0.5)\nprovisional marks + justification\n+ feedback", BLUE_SOFT, BLUE, fs=8.8)
arrow(ax, CX, 66, CX, 63.0, lw=1.5)
# verify
center_box(56, 7.0, "verify (Verifier, T=0.2)\nrecompute mark, hunt hallucinations,\nconfidence_pct", BLUE_SOFT, BLUE, fs=8.8)
arrow(ax, CX, 56, CX, 52.8, lw=1.5)
# decide
center_box(45.5, 7.3, "decide", "#F2F4F7", "#B9C2CC", fs=9.6, bold=True)

# branches - three boxes side by side
box(ax, 4, 30, 26, 9, "approved", W, fc=GREEN_SOFT, ec=GREEN, fs=9.6, bold=True)
box(ax, 37, 26, 26, 13, "retry  (max 2 rounds)\ncritique fed back\nto Marker", W, fc=ORANGE_SOFT, ec=ORANGE, fs=8.6)
box(ax, 70, 30, 26, 9, "flagged\nfor teacher review", W, fc=RED_SOFT, ec=RED, fs=8.8)

# decide -> branches (edge to edge)
arrow(ax, 30, 49.2, 17, 39.2, color=GREEN, lw=1.6)   # decide left edge -> approved top-right
arrow(ax, CX, 45.5, CX, 39.2, color=GRAY, lw=1.5)     # decide bottom -> retry top
arrow(ax, 70, 49.2, 83, 39.2, color=RED, lw=1.6)      # decide right edge -> flagged top-left

# retry -> grade (loop back, right side of central column)
arrow(ax, 63, 29, 63, 62.8, color=ORANGE, lw=1.5, label="retry loop")

# outputs at bottom
box(ax, 4, 6, 26, 12, "OUTPUT: approved\nmarks + confidence_pct\n+ refined feedback", W, fc=GREEN_SOFT, ec=GREEN, fs=8.6)
box(ax, 70, 6, 26, 12, "OUTPUT: flagged\nsent to teacher UI\nwith explainable flags", W, fc=RED_SOFT, ec=RED, fs=8.6)
arrow(ax, 17, 30, 17, 18.2, color=GREEN, lw=1.5)
arrow(ax, 83, 30, 83, 18.2, color=RED, lw=1.5)

fig.savefig(f"{OUT}/workflow1.png", dpi=200, bbox_inches="tight", facecolor=PAPER)
plt.close(fig)
print("OK workflow1 v2")

# ================================================================ 3. MODEL ABSTRACTION
W = 8.8
fig, ax = new_ax(W, 5.0,
    "Model Abstraction Layer",
    "Pipeline code never imports an SDK - agents call agents.models.complete() only")

# top: pipeline boxes
box(ax, 4, 82, 90, 8, "", W, fc="#F2F4F7", ec="#C9D3DE")
ax.text(5.5, 88.4, "PIPELINE (unchanged when the model changes)", fontsize=7.8,
        fontweight="bold", color=GRAY, va="center")
box(ax, 7, 83.2, 24, 5.6, "mark_graph.py", W, fc="#FFFFFF", ec="#9FB0C0", fs=8.8)
box(ax, 38, 83.2, 24, 5.6, "marker.py", W, fc="#FFFFFF", ec="#9FB0C0", fs=8.8)
box(ax, 69, 83.2, 24, 5.6, "verifier.py", W, fc="#FFFFFF", ec="#9FB0C0", fs=8.8)
arrow(ax, 50, 82, 50, 76.2, color=BLUE, lw=2)
# the single entry point
box(ax, 36, 66, 28, 10.2, "complete(system,\nuser, temperature)", W, fc=BLUE_SOFT, ec=BLUE, fs=9.4, bold=True)
arrow(ax, 50, 66, 50, 60.4, color=BLUE, lw=2)
# provider cards
box(ax, 3, 30, 28, 30, "", W, fc="#F2F4F7", ec="#C9D3DE")
box(ax, 6, 51, 22, 7, "deepseek-v4-flash", W, fc=GREEN_SOFT, ec=GREEN, fs=9.2, bold=True)
ax.text(17, 45.5, "ACTIVE NOW\n(your key)", fontsize=7.8, color=GREEN, ha="center", va="center", fontweight="bold")
box(ax, 36, 30, 28, 30, "", W, fc="#F2F4F7", ec="#C9D3DE")
box(ax, 39, 51, 22, 7, "gemini 3.5 flash", W, fc="#FFFFFF", ec="#B9C2CC", fs=9.2)
ax.text(50, 45.5, "free tier\n(future)", fontsize=7.8, color=GRAY, ha="center", va="center")
box(ax, 69, 30, 28, 30, "", W, fc="#F2F4F7", ec="#C9D3DE")
box(ax, 72, 51, 22, 7, "ollama local", W, fc="#FFFFFF", ec="#B9C2CC", fs=9.2)
ax.text(83, 45.5, "open-weight\nstory", fontsize=7.8, color=GRAY, ha="center", va="center")
arrow(ax, 17, 42.8, 17, 30.2, color=GREEN, lw=1.6)
arrow(ax, 50, 42.8, 50, 30.2, color=GRAY, lw=1.4)
arrow(ax, 83, 42.8, 83, 30.2, color=GRAY, lw=1.4)
# bottom callout
box(ax, 3, 4, 94, 20, "", W, fc="#FDF6E8", ec=ORANGE)
ax.text(50, 17, "Why it matters", fontsize=9, fontweight="bold", color="#B26A00",
        ha="center")
ax.text(50, 12.5, "Swapping providers is one config line: the state machine, RAG,\nprompts, feedback logic and UI never change.", fontsize=8.6,
        color=INK, ha="center", va="center")

fig.savefig(f"{OUT}/model_abstraction.png", dpi=200, bbox_inches="tight", facecolor=PAPER)
plt.close(fig)
print("OK model_abstraction v2")

# ================================================================ 4. GOLDEN RESULTS
fig, ax = plt.subplots(figsize=(8.6, 5.1))
ax.set_facecolor(PAPER)
groups = ["Excellent", "Good", "Weak", "Borderline"]
exact = [100.0, 87.5, 75.0, 50.0]
x = list(range(len(groups)))
colors = [BLUE, "#7E9CBE", "#A9BBD1", "#C4D0DD"]
bars = ax.bar(x, exact, width=0.5, color=colors, zorder=3)
for xi, e in zip(x, exact):
    ax.text(xi, e + 4, f"{e:.0f}%", ha="center", fontsize=12,
            fontweight="bold", color=INK if e == 100 else "#4A5568", zorder=5)

ax.set_xticks(x)
ax.set_xticklabels(groups, fontsize=11.5)
ax.set_ylim(0, 128)
ax.set_ylabel("Exact match with official rubric (%)", fontsize=10)
ax.set_title("32/32 answers graded within +/-1 band of the official rubric - zero wild misses",
             fontsize=12.5, fontweight="bold", color=INK, loc="left", pad=16)
ax.grid(axis="y", color="#E5E9EF", lw=0.8, zorder=0)
ax.spines[["top", "right"]].set_visible(False)
ax.spines[["left", "bottom"]].set_color("#C9D3DE")

# legend OUTSIDE the data area, top-right above plot
handles = [
    mlines.Line2D([], [], color=BLUE, lw=6, label="exact match", solid_capstyle="butt"),
    mlines.Line2D([], [], color=GREEN, lw=0, marker="_", markersize=14,
                  label="+/-1 band agreement: 100% (all bands)"),
]
ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 1.02),
          ncol=2, fontsize=9.5, frameon=False)
fig.text(0.985, 0.012,
         "n = 32 simulated answers (8 questions x 4 quality bands) | expected marks from official NESA marking guidelines",
         ha="right", fontsize=8, color=GRAY)
fig.savefig(f"{OUT}/golden_results.png", dpi=200, bbox_inches="tight", facecolor=PAPER)
plt.close(fig)
print("OK golden_results v2")
