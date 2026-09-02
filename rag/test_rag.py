#!/usr/bin/env python3
"""End-to-end RAG smoke test: 3 real queries against the indexed NESA TSR corpus.

Run after indexer.py has built the Chroma DB:
    python3 test_rag.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from retriever import search  # noqa: E402

QUERIES = [
    "benefits of cloud computing",
    "data visualisation storytelling",
    "expert systems inference engine",
]


def main():
    for q in QUERIES:
        print("=" * 78)
        print(f"QUERY: {q!r}")
        print("=" * 78)
        hits = search(q, k=5)
        if not hits:
            print("  (no hits returned)")
            continue
        for i, h in enumerate(hits, 1):
            snippet = h["text"][:200].replace("\n", " ")
            print(f"\n[{i}] score={h['score']} | source={h['source']} | topic={h['topic']}")
            print(f"    {snippet}...")
    print("\n" + "=" * 78)
    print("RAG smoke test finished.")


if __name__ == "__main__":
    main()
