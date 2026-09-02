#!/usr/bin/env python3
"""CoachAI RAG retriever — semantic search over the NESA TSR Chroma collection.

Usage:
    from retriever import search
    hits = search("benefits of cloud computing", k=5)
    hits = search("data storytelling", k=3, topic="data-visualisation")

CLI:
    python3 retriever.py "expert systems inference engine" [--k 5] [--topic X]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from indexer import get_embedding_function  # noqa: E402  (shared embedding factory)

DB_DIR = os.environ.get(
    "COACHAI_CHROMA_DIR",
    "/home/gaogao/workspace/ai-coach/data/chroma_db",
)
COLLECTION = "tsr_docs"

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        import chromadb
        ef, _label = get_embedding_function()
        _client = chromadb.PersistentClient(path=DB_DIR)
        _collection = _client.get_collection(COLLECTION, embedding_function=ef)
    return _collection


def search(query, k=5, topic=None):
    """Return top-k hits as [{text, source, topic, score}], score ~ cosine similarity."""
    col = _get_collection()
    where = {"topic": topic} if topic else None
    res = col.query(
        query_texts=[query],
        n_results=k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    hits = []
    for text, meta, dist in zip(docs, metas, dists):
        # cosine space -> similarity, clipped to [0, 1]
        score = max(0.0, min(1.0, 1.0 - dist))
        hits.append({
            "text": text,
            "source": (meta or {}).get("source", "?"),
            "topic": (meta or {}).get("topic", "?"),
            "score": round(score, 4),
        })
    return hits


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Semantic search over NESA TSR docs")
    ap.add_argument("query")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--topic", default=None)
    args = ap.parse_args()
    for i, h in enumerate(search(args.query, k=args.k, topic=args.topic), 1):
        print(f"\n--- hit {i} | score={h['score']} | source={h['source']} | topic={h['topic']}")
        print(h["text"][:400])
