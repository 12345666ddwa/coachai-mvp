#!/usr/bin/env python3
"""
CoachAI Workflow 1 — LangGraph marker+verifier state machine with RAG.

Pipeline for one student answer:

    load_question ─▶ retrieve (RAG, k=4) ─▶ grade (Marker) ─▶ verify (Verifier)
                                                                    │
        approved ───────────────────────────────────────────────────┤
        rejected & attempts<2 ─▶ retry (attempts+1, feeds critique back to Marker) ─▶ grade
        rejected & attempts>=2 ─▶ finalize (status="flagged")

Final confidence is NOT the model's raw self-report: it is blended with
marker/verifier agreement in the finalize node:

    base = model_confidence_pct * 0.6
         + 20 if marker.marks == verifier.final_marks
         + 10 if |diff| == 1
         +  0 if |diff| >= 2
         + 10 if verifier approved
    clamp: floor 25, cap 95

Public interface (used by the Gradio UI and everywhere else):

    result = mark_answer(question_id, student_answer)
"""
import copy
import hashlib
import json
import os
import sys
from typing import Optional, TypedDict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from agents.marker import mark as marker_mark  # noqa: E402
from agents.verifier import verify as verifier_verify  # noqa: E402

try:
    from langgraph.graph import END, START, StateGraph
except ImportError as exc:  # pragma: no cover
    raise SystemExit("langgraph is not installed — run: pip install langgraph") from exc

QUESTIONS_PATH = os.path.join(_ROOT, "data", "questions.json")
RAG_K = 4
MAX_RETRIES = 2          # max extra marker+verifier rounds after a rejection
CONF_CAP, CONF_FLOOR = 95, 25


# ------------------------------------------------------------------- state

class MarkState(TypedDict):
    question_id: str
    student_answer: str
    question: Optional[dict]           # loaded from data/questions.json
    retrieved_docs: list               # RAG hits [{text, source, topic, score}]
    provisional: Optional[dict]        # marker output
    verified: Optional[dict]           # verifier output
    attempts: int                      # retry rounds executed so far
    critique: str                      # accumulated verifier critique fed to marker
    result: Optional[dict]             # final assembled result


# ------------------------------------------------------------------- helpers

def load_question_by_id(question_id: str) -> dict:
    """Find a question dict in data/questions.json by its id."""
    with open(QUESTIONS_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    for q in data.get("questions", []):
        if q.get("id") == question_id:
            return q
    raise ValueError(f"[mark_graph] unknown question_id: {question_id!r} "
                     f"(valid ids in {QUESTIONS_PATH})")


def _require(state: MarkState, key: str) -> dict:
    """Unwrap a node-produced dict field; raise a clear error if missing."""
    value = state[key]
    if value is None:
        raise RuntimeError(f"[mark_graph] internal error: state.{key} is None — "
                           "graph nodes executed out of order?")
    return value


# ------------------------------------------------------------------- nodes

def node_load_question(state: MarkState) -> dict:
    question = load_question_by_id(state["question_id"])
    return {"question": question}


def node_retrieve(state: MarkState) -> dict:
    """RAG retrieval — query built from the question stem, top-k = 4."""
    question = _require(state, "question")
    try:
        from rag.retriever import search
        hits = search(question["text"], k=RAG_K) or []
    except Exception as exc:  # retrieval must never kill the pipeline
        hits = []
        print(f"[mark_graph] RAG retrieval unavailable, continuing without docs: {exc}")
    return {"retrieved_docs": hits}


def node_grade(state: MarkState) -> dict:
    question = _require(state, "question")
    critique = state["critique"] or None
    provisional = marker_mark(
        question,
        state["student_answer"],
        state["retrieved_docs"],
        critique=critique,
    )
    return {"provisional": provisional}


def node_verify(state: MarkState) -> dict:
    question = _require(state, "question")
    provisional = _require(state, "provisional")
    verified = verifier_verify(
        question,
        provisional,
        state["student_answer"],
        state["retrieved_docs"],
    )
    return {"verified": verified}


def _critique_text(state: MarkState) -> str:
    """Human-readable critique bundle from the latest verifier round."""
    verified = _require(state, "verified")
    provisional = _require(state, "provisional")
    bits = []
    if verified.get("flags"):
        bits.append("Verifier flags: " + "; ".join(verified["flags"]))
    m_marks = provisional.get("marks")
    v_marks = verified.get("final_marks")
    if m_marks != v_marks:
        bits.append(f"Score disagreement: marker awarded {m_marks}, "
                    f"verifier recomputed {v_marks} — re-examine the rubric bands "
                    "and adjust the mark if you were wrong.")
    else:
        bits.append("Verifier agrees on the score but rejected the verdict for "
                    "other reasons (see flags) — fix them.")
    bits.append("Re-grade carefully and stay within the rubric.")
    return " | ".join(bits)


def node_retry(state: MarkState) -> dict:
    """One rejection round: bump attempts, append critique for the marker."""
    prev = state["critique"]
    new_bit = _critique_text(state)
    critique = (prev + "\n\n" + new_bit) if prev else new_bit
    return {"attempts": state["attempts"] + 1, "critique": critique}


def _blend_confidence(provisional: dict, verified: dict) -> int:
    """Hybrid confidence: model self-report *0.6 + agreement bonus + approval bonus."""
    base = float(verified.get("confidence_pct", 0)) * 0.6
    diff = abs(int(provisional.get("marks", 0)) - int(verified.get("final_marks", 0)))
    if diff == 0:
        base += 20
    elif diff == 1:
        base += 10
    if verified.get("is_approved"):
        base += 10
    return max(CONF_FLOOR, min(CONF_CAP, int(round(base))))


def _confidence_level(pct: int) -> str:
    if pct >= 80:
        return "high"
    if pct >= 50:
        return "medium"
    return "low"


def node_finalize(state: MarkState) -> dict:
    question = _require(state, "question")
    provisional = _require(state, "provisional")
    verified = _require(state, "verified")

    is_approved = bool(verified.get("is_approved"))
    confidence = _blend_confidence(provisional, verified)
    status = "approved" if is_approved else "flagged"

    justification = str(provisional.get("justification", ""))
    flags = verified.get("flags", [])
    if status == "flagged" and flags:
        justification += " [QA audit unresolved] " + " ".join(flags)

    result = {
        "question_id": state["question_id"],
        "status": status,
        "marks": int(verified.get("final_marks", 0)),
        "max_marks": int(provisional.get("max_marks", question.get("marks", 0))),
        "confidence_pct": confidence,
        "confidence_level": _confidence_level(confidence),
        "feedback": verified.get("refined_feedback") or provisional.get("feedback", []),
        "flags": flags,
        "attempts": state["attempts"] + 1,  # total marker+verifier rounds
        "justification": justification,
    }
    return {"result": result}


# ------------------------------------------------------------------- routing

def route_after_verify(state: MarkState) -> str:
    """decide branch: approve / retry / give up (flag)."""
    verified = _require(state, "verified")
    if verified.get("is_approved"):
        return "approve"
    if state["attempts"] < MAX_RETRIES:
        return "retry"
    return "give_up"


def build_graph():
    """Build (once) and compile the LangGraph state machine."""
    g = StateGraph(MarkState)
    g.add_node("load_question", node_load_question)
    g.add_node("retrieve", node_retrieve)
    g.add_node("grade", node_grade)
    g.add_node("verify", node_verify)
    g.add_node("retry", node_retry)
    g.add_node("finalize", node_finalize)

    g.add_edge(START, "load_question")
    g.add_edge("load_question", "retrieve")
    g.add_edge("retrieve", "grade")
    g.add_edge("grade", "verify")
    g.add_conditional_edges(
        "verify",
        route_after_verify,
        {"approve": "finalize", "retry": "retry", "give_up": "finalize"},
    )
    g.add_edge("retry", "grade")
    g.add_edge("finalize", END)
    return g.compile()


# ------------------------------------------------------------------- public API

_GRAPH = None
_CACHE: dict[str, dict] = {}
CACHE_HITS = 0  # exposed for tests


def _graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def _cache_key(question_id: str, student_answer: str) -> str:
    digest = hashlib.sha1((student_answer or "").strip()[:50].encode("utf-8")).hexdigest()
    return f"{question_id}::{digest}"


def mark_answer(question_id: str, student_answer: str) -> dict:
    """Unified project entry point for grading one answer.

    Returns the final result dict — never raises (errors are returned as
    {"status": "error", "error": ...}). Identical (question_id, answer-prefix)
    requests are served from an in-memory cache.
    """
    global CACHE_HITS
    if not isinstance(student_answer, str) or not student_answer.strip():
        return {"status": "error", "error": "student_answer must be a non-empty string"}

    key = _cache_key(question_id, student_answer)
    if key in _CACHE:
        CACHE_HITS += 1
        return copy.deepcopy(_CACHE[key])

    try:
        initial = MarkState(
            question_id=question_id,
            student_answer=student_answer,
            question=None,
            retrieved_docs=[],
            provisional=None,
            verified=None,
            attempts=0,
            critique="",
            result=None,
        )
        final_state = _graph().invoke(initial)
        result = final_state.get("result")
        if not isinstance(result, dict) or result.get("status") not in ("approved", "flagged"):
            raise RuntimeError(f"[mark_graph] pipeline finished without a valid result: {result}")
        _CACHE[key] = copy.deepcopy(result)
        return result
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}


def clear_cache() -> None:
    """Empty the in-memory result cache (mainly for tests)."""
    _CACHE.clear()


if __name__ == "__main__":  # quick manual check
    import pprint
    r = mark_answer("ec2025-q14", "Memes are funny pictures that people share.")
    pprint.pprint(r)
