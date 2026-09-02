#!/usr/bin/env python3
"""Generate 4 professional figures for the CoachAI report (PNG, 200dpi)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches

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

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": "#CCCCCC",
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
})

def box(ax, x, y, w, h, text, fc=BLUE_SOFT, ec=BLUE, tc=INK, fs=10, bold=False, rounded=True):
    style = "round,pad=0.02,rounding_size=0.08" if rounded else "square,pad=0.02"
    p = FancyBboxPatch((x, y), w, h, boxstyle=style, linewidth=1.4,
                       facecolor=fc, edgecolor=ec, zorder=3)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=tc, zorder=4, fontweight="bold" if bold else "normal",
            wrap=True)
    return p

def arrow(ax, x1, y1, x2, y2, color=GRAY, lw=1.8, style="-|>", label=None, ls="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
                        linewidth=lw, color=color, zorder=2, linestyle=ls)
    ax.add_patch(a)
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.06, label, ha="center", va="bottom",
                fontsize=8.5, color=color, zorder=5)

def new_ax(w, h, title=None, subtitle=None):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    if title:
        ax.text(0, 100.8, title, fontsize=13, fontweight="bold", color=INK, va="top")
    if subtitle:
        ax.text(0, 97.3, subtitle, fontsize=9.5, color=GRAY, va="top")
    return fig, ax

# ============================================================ 1. architecture
fig, ax = new_ax(10.2, 5.6,
    "CoachAI System Architecture",
    "Two LangGraph workflows share one RAG knowledge base and one model abstraction layer")
y_off = 4.0

# Data layer
box(ax, 2, 8.5, 96, 9, "", fc="#F5F6F8", ec="#DDDDDD")
ax.text(3.2, 16.1, "DATA LAYER", fontsize=8.5, fontweight="bold", color=GRAY)
box(ax, 5, 9.4, 40, 6.4, "NESA official materials\nsyllabus + TSRs (4 modules)", fc="#F5F6F8", ec="#BBBBBB")
box(ax, 55, 9.4, 40, 6.4, "Question bank\n18 questions (2025 HSC) + official\nmarking guidelines", fc="#F5F6F8", ec="#BBBBBB")

# Graph layer
box(ax, 2, 47, 96, 11, "", fc="#FBF7EF", ec="#E8D5B0")
ax.text(3.2, 54.8, "LANGGRAPH LAYER", fontsize=8.5, fontweight="bold", color="#B26A00")
box(ax, 5, 48.2, 42, 8, "Graph A: mark_graph\nshort-answer marking", fc=ORANGE_SOFT, ec=ORANGE)
box(ax, 53, 48.2, 42, 8, "Graph B: report_graph\nreport feedback (next phase)", fc=ORANGE_SOFT, ec=ORANGE, tc=GRAY)

# Agent layer
box(ax, 2, 85.5, 96, 11, "", fc="#EFF4FB", ec="#B8CCE4")
ax.text(3.2, 93.3, "AGENT LAYER", fontsize=8.5, fontweight="bold", color=BLUE)
box(ax, 5, 86.6, 42, 8, "Marker Agent (T=0.5)\nHSC teacher: award marks + feedback", fc=BLUE_SOFT, ec=BLUE)
box(ax, 53, 86.6, 42, 8, "Verifier Agent (T=0.2)\nQA auditor: audit, confidence, flags", fc=BLUE_SOFT, ec=BLUE)

# Service layer
box(ax, 30, 64, 40, 9, "", fc="#F0F7F0", ec="#B7D7B7")
ax.text(31.8, 71.5, "SERVICE LAYER", fontsize=8.5, fontweight="bold", color=GREEN)
box(ax, 33, 65.2, 34, 5.6, "Gradio UI  |  FastAPI-ready\nphone-friendly web demo", fc=GREEN_SOFT, ec=GREEN)

# Model layer (right rail)
box(ax, 76, 30, 22, 52, "", fc="#FBEEEE", ec="#E5B8B8")
ax.text(77.2, 80, "MODEL\nABSTRACTION", fontsize=8, fontweight="bold", color=RED, ha="left")
box(ax, 77.4, 68, 19.2, 7, "deepseek-v4-flash\n(active now)", fc=RED_SOFT, ec=RED, fs=7.6)
box(ax, 77.4, 56, 19.2, 7, "gemini 3.5 flash\nfree tier", fc=RED_SOFT, ec=RED, fs=7.6, tc=GRAY)
box(ax, 77.4, 44, 19.2, 7, "ollama local\nopen-weight", fc=RED_SOFT, ec=RED, fs=7.6, tc=GRAY)
box(ax, 77.4, 33, 19.2, 6, "swap = one\nconfig line", fc="#FFFFFF", ec=RED, fs=7.5, tc=RED)

# Arrows: data -> graph -> agents -> service; rag into graph
arrow(ax, 30, 15.8, 30, 47.5, color=GRAY, lw=2)
arrow(ax, 75, 15.8, 75, 47.5, color=GRAY, lw=2)
arrow(ax, 30, 56.5, 30, 85.5, color=BLUE, lw=2)
arrow(ax, 75, 56.5, 75, 85.5, color=BLUE, lw=2)
arrow(ax, 50, 90.5, 62, 70.5, color=GREEN, lw=2)
# RAG retriever note
box(ax, 5, 30, 20, 12, "RAG retriever\nChroma vector DB\n1,046 chunks", fc="#F5F6F8", ec="#BBBBBB", fs=8.5)
arrow(ax, 15, 42, 26, 50.5, color=ORANGE, lw=1.8, label="retrieval")

fig.savefig(f"{OUT}/architecture.png", dpi=200, bbox_inches="tight", facecolor=PAPER)
plt.close(fig)
print("OK architecture.png")

# ============================================================ 2. workflow1
fig, ax = new_ax(10.2, 6.4,
    "Workflow 1: Short-Answer Marking (LangGraph State Machine)",
    "Every node is deterministic; all LLM calls go through the model abstraction layer")

# Nodes: vertical-ish flow
box(ax, 42, 88, 16, 8, "INPUT\nquestion_id +\nstudent answer", fc="#F5F6F8", ec="#BBBBBB", fs=9)
arrow(ax, 50, 88, 50, 83.5)
box(ax, 40, 75, 20, 8.5, "load_question\npull question + official\nmarking guidelines", fc=BLUE_SOFT, ec=BLUE, fs=9)
arrow(ax, 50, 75, 50, 70)
box(ax, 40, 61, 20, 9, "retrieve (RAG)\n4 syllabus chunks\ninto the prompt", fc=ORANGE_SOFT, ec=ORANGE, fs=9)
arrow(ax, 50, 61, 50, 55.5)
box(ax, 40, 46, 20, 9.5, "grade (Marker)\nprovisional marks +\njustification + feedback", fc=BLUE_SOFT, ec=BLUE, fs=9)
arrow(ax, 50, 46, 50, 41)
box(ax, 40, 32.5, 20, 8.5, "verify (Verifier)\nrecompute mark, hunt\nhallucinations, confidence", fc=BLUE_SOFT, ec=BLUE, fs=9)

# Branch
arrow(ax, 50, 32.5, 50, 28, color=GREEN, lw=1.8)
box(ax, 40, 19, 20, 9, "decide", fc="#F5F6F8", ec="#BBBBBB", fs=9, bold=True)
box(ax, 8, 12, 22, 8, "approved", fc=GREEN_SOFT, ec=GREEN, fs=9)
box(ax, 39, 8, 22, 8, "retry (<=2 rounds)\ncritique fed back\nto Marker", fc=ORANGE_SOFT, ec=ORANGE, fs=8.5)
box(ax, 70, 12, 22, 8, "flagged\nfor teacher review", fc=RED_SOFT, ec=RED, fs=9)
arrow(ax, 42, 23.5, 19, 20.5, color=GREEN, lw=1.8)
arrow(ax, 50, 19, 50, 16.5, color=GRAY, lw=1.6)
arrow(ax, 61, 12, 70, 12, color=ORANGE, lw=1.8)
arrow(ax, 19, 12, 19, 3.5, color=GRAY, lw=1.6, style="-")
arrow(ax, 81, 12, 81, 3.5, color=GRAY, lw=1.6, style="-")
box(ax, 5, -2.5, 30, 5.5, "OUTPUT: marks + confidence_pct\n+ refined feedback", fc=GREEN_SOFT, ec=GREEN, fs=8.5)
box(ax, 65, -2.5, 30, 5.5, "OUTPUT: flagged + teacher UI\nexplainable flags", fc=RED_SOFT, ec=RED, fs=8.5)

fig.savefig(f"{OUT}/workflow1.png", dpi=200, bbox_inches="tight", facecolor=PAPER)
plt.close(fig)
print("OK workflow1.png")

# ============================================================ 3. model abstraction
fig, ax = new_ax(8.6, 4.6,
    "Model Abstraction Layer: swap providers without touching the pipeline",
    "agents/marker.py and verifier.py call agents.models.complete() only")

box(ax, 5, 75, 90, 12, "", fc="#F5F6F8", ec="#DDDDDD")
ax.text(6.5, 84.5, "PIPELINE CODE (unchanged)", fontsize=8, fontweight="bold", color=GRAY)
box(ax, 8, 76.5, 26, 7, "mark_graph.py", fc="#FFFFFF", ec="#BBBBBB", fs=8.5)
box(ax, 38, 76.5, 26, 7, "marker.py", fc="#FFFFFF", ec="#BBBBBB", fs=8.5)
box(ax, 68, 76.5, 26, 7, "verifier.py", fc="#FFFFFF", ec="#BBBBBB", fs=8.5)
arrow(ax, 50, 75, 50, 68)
box(ax, 38, 58, 24, 10, "complete(system,\nuser, temperature)", fc=BLUE_SOFT, ec=BLUE, fs=9, bold=True)
arrow(ax, 50, 58, 50, 52, color=BLUE, lw=2)
# providers
box(ax, 3, 32, 28, 20, "", fc="#F5F6F8", ec="#DDDDDD")
box(ax, 6, 43, 22, 6, "deepseek-v4-flash", fc=GREEN_SOFT, ec=GREEN, fs=9, bold=True)
box(ax, 6, 35, 22, 6, "ACTIVE NOW (your key)", fc="#FFFFFF", ec=GREEN, fs=7.5, tc=GREEN)
box(ax, 36, 32, 28, 20, "", fc="#F5F6F8", ec="#DDDDDD")
box(ax, 39, 43, 22, 6, "gemini 3.5 flash", fc="#FFFFFF", ec="#BBBBBB", fs=9)
box(ax, 39, 35, 22, 6, "free tier - future", fc="#FFFFFF", ec="#BBBBBB", fs=7.5, tc=GRAY)
box(ax, 69, 32, 28, 20, "", fc="#F5F6F8", ec="#DDDDDD")
box(ax, 72, 43, 22, 6, "ollama (local)", fc="#FFFFFF", ec="#BBBBBB", fs=9)
box(ax, 72, 35, 22, 6, "open-weight story", fc="#FFFFFF", ec="#BBBBBB", fs=7.5, tc=GRAY)
arrow(ax, 17, 32, 17, 6, color=GREEN, lw=1.6)
arrow(ax, 50, 32, 50, 6, color=GRAY, lw=1.2)
arrow(ax, 83, 32, 83, 6, color=GRAY, lw=1.2)
box(ax, 3, -4, 94, 8, "Why it matters: swapping the model is ONE config line - the state machine, RAG, prompts and UI never change.", fc=ORANGE_SOFT, ec=ORANGE, fs=8.5)

fig.savefig(f"{OUT}/model_abstraction.png", dpi=200, bbox_inches="tight", facecolor=PAPER)
plt.close(fig)
print("OK model_abstraction.png")

# ============================================================ 4. golden results (SWD style)
fig, ax = plt.subplots(figsize=(8.8, 4.9))
ax.set_facecolor(PAPER)

groups = ["Excellent", "Good", "Weak", "Borderline"]
exact = [100.0, 87.5, 75.0, 50.0]
within1 = [100.0, 100.0, 100.0, 100.0]
x = range(len(groups))

# single-emphasis style: excellent highlighted, others gray
colors = [BLUE, "#9FB6CE", "#B9C7D6", "#C9D3DE"]
bars = ax.bar(x, exact, width=0.52, color=colors, zorder=3)
# ±1 band = 100% markers
for xi, (e, w1) in enumerate(zip(exact, within1)):
    ax.plot([xi - 0.26, xi + 0.26], [w1, w1], color=GREEN, lw=2.2, zorder=4)
    ax.text(xi + 0.32, w1 + 1.5, "100%", fontsize=8, color=GREEN, fontweight="bold",
            ha="left", va="bottom")

for xi, e in zip(x, exact):
    ax.text(xi, e + 2.5, f"{e:.0f}%", ha="center", fontsize=11, fontweight="bold",
            color=INK if e == 100 else GRAY)

ax.set_xticks(list(x))
ax.set_xticklabels(groups, fontsize=11)
ax.set_ylim(0, 118)
ax.set_ylabel("Exact-match rate (%)", fontsize=10)
ax.set_title("All 32 answers graded within ±1 band of the official rubric - zero wild misses",
             fontsize=12, fontweight="bold", color=INK, loc="left", pad=14)
ax.grid(axis="y", color="#E5E9EF", lw=0.8, zorder=0)
ax.spines[["top", "right"]].set_visible(False)
ax.spines[["left", "bottom"]].set_color("#CCCCCC")

legend_patches = [
    mpatches.Patch(color=BLUE, label="exact match with official rubric"),
    mpatches.Patch(color="none", label=""),
    mpatches.Patch(color="none", label=""),
]
line_handle = plt.Line2D([0], [0], color=GREEN, lw=2.2, label="±1 band agreement = 100% (all groups)")
ax.legend(handles=[legend_patches[0], line_handle], loc="lower right", fontsize=9,
          frameon=False)

fig.text(0.98, 0.015, "n = 32 simulated answers (8 questions x 4 quality bands) | expected marks from official NESA marking guidelines",
         ha="right", fontsize=8, color=GRAY)
fig.savefig(f"{OUT}/golden_results.png", dpi=200, bbox_inches="tight", facecolor=PAPER)
plt.close(fig)
print("OK golden_results.png")
