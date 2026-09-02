#!/usr/bin/env python3
"""CoachAI RAG indexer — NESA Teacher Support Resources (TSR) .docx -> Chroma vector store.

Extracts text from BOTH body paragraphs and table cells (in real document order),
splits by Heading-style paragraphs into chunks, further splits oversized chunks
(~1000 chars, 100-char overlap), and persists everything into a local Chroma DB.

Usage:
    python3 indexer.py [DOCX_DIR] [DB_DIR] [COLLECTION]
"""
import os
import re
import sys
import glob

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from docx.document import Document as _Doc

# ---------------------------------------------------------------- config
DOCX_DIR = sys.argv[1] if len(sys.argv) > 1 else "/mnt/c/Users/18613/Desktop/新建文件夹"
DB_DIR = sys.argv[2] if len(sys.argv) > 2 else "/home/gaogao/workspace/ai-coach/data/chroma_db"
COLLECTION = sys.argv[3] if len(sys.argv) > 3 else "tsr_docs"

CHUNK_TARGET = 1000      # ~1000 chars per chunk
OVERLAP = 100            # 100-char overlap between split pieces
SPLIT_THRESHOLD = 1200   # chunks longer than this get split

# explicit topic map, keyed on a token found in the filename
TOPIC_HINTS = [
    ("data-science", "data-science"),
    ("data-visualisation", "data-visualisation"),
    ("data-visualization", "data-visualisation"),
    ("enterprise-project", "enterprise-project"),
    ("intelligent", "intelligent-systems"),
]

HEADING_STYLE_RE = re.compile(r"^(heading\s*\d+|title)$", re.I)


# ---------------------------------------------------------------- embedding
def get_embedding_function():
    """Prefer sentence-transformers MiniLM; fall back to Chroma's default ONNX MiniLM."""
    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        ef(["probe"])  # triggers model load / download so failures surface early
        return ef, "sentence-transformers/all-MiniLM-L6-v2"
    except Exception as e:
        print(f"[indexer] sentence-transformers unavailable ({e}); "
              f"falling back to chromadb DefaultEmbeddingFunction (ONNX MiniLM)")
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        return DefaultEmbeddingFunction(), "chromadb-default-embedding (ONNX all-MiniLM-L6-v2)"


# ---------------------------------------------------------------- extraction
def _is_heading(paragraph):
    try:
        return bool(paragraph.style and HEADING_STYLE_RE.match(paragraph.style.name or ""))
    except Exception:
        return False


def iter_blocks(parent):
    """Yield Paragraph / Table objects in document order, recursing into cells."""
    parent_elm = parent.element.body if isinstance(parent, _Doc) else parent._tc
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _clean(text):
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def cell_lines(cell):
    """All text lines inside a table cell (recurses into nested tables)."""
    lines = []
    for block in iter_blocks(cell):
        if isinstance(block, Paragraph):
            t = _clean(block.text)
            if t:
                lines.append(t)
        else:  # nested table -> flatten row by row
            for row in block.rows:
                parts = [_clean(c.text) for c in row.cells]
                parts = [p for p in parts if p]
                if parts:
                    lines.append(" | ".join(parts))
    return lines


def table_lines(table):
    """One line per non-empty table row; cells joined with ' | '."""
    rows = []
    for row in table.rows:
        parts = [_clean(c.text) for c in row.cells]
        parts = [p for p in parts if p]
        if parts:
            rows.append(" | ".join(parts))
    return rows


def extract_document_lines(doc):
    """Yield (text, is_heading) lines for the whole document body, in order."""
    for block in iter_blocks(doc):
        if isinstance(block, Paragraph):
            t = _clean(block.text)
            if t:
                yield t, _is_heading(block)
        else:
            for row_line in table_lines(block):
                yield row_line, False


# ---------------------------------------------------------------- chunking
def split_long_chunk(text, heading_prefix, size=CHUNK_TARGET, overlap=OVERLAP):
    """Split an oversized chunk into ~size-char windows with `overlap` chars of overlap.

    Tries to break at sentence/line boundaries; keeps the section heading as a
    prefix on every piece so each piece stays self-contained.
    """
    pieces = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:  # look backwards for a nice boundary inside the window
            window = text[start:end]
            cut = -1
            for m in re.finditer(r"(?<=[.\n;:])\s+", window):
                pos = m.end()
                if pos >= size * 0.6:  # only accept boundary in the latter part
                    cut = pos
                    break
            if cut != -1:
                end = start + cut
        piece = text[start:end].strip()
        if piece:
            pieces.append((heading_prefix + "\n" + piece) if heading_prefix else piece)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return pieces


def build_chunks(lines):
    """Group heading+content lines into chunks; split oversized ones."""
    chunks = []          # list of (chunk_text)
    buf = []
    heading_prefix = None

    def flush():
        nonlocal buf
        if buf:
            text = "\n".join(buf)
            if len(text) > SPLIT_THRESHOLD:
                chunks.extend(split_long_chunk(text, heading_prefix))
            else:
                chunks.append(text)
        buf = []

    for text, is_heading in lines:
        if is_heading:
            flush()
            heading_prefix = text
            buf.append(text)
        else:
            buf.append(text)
    flush()
    return chunks


def infer_topic(filename):
    base = os.path.basename(filename).lower()
    for token, topic in TOPIC_HINTS:
        if token in base:
            return topic
    stem = re.sub(r"[^a-z0-9]+", "-", os.path.splitext(base)[0]).strip("-")
    return stem or "unknown"


def safe_id(filename, i):
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", os.path.splitext(os.path.basename(filename))[0])
    return f"{stem}--{i:06d}"


# ---------------------------------------------------------------- indexing
def main():
    import chromadb

    docx_files = sorted(glob.glob(os.path.join(DOCX_DIR, "*.docx")))
    if not docx_files:
        print(f"[indexer] no .docx files found in {DOCX_DIR}")
        sys.exit(1)

    ef, ef_label = get_embedding_function()
    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        client.delete_collection(COLLECTION)  # fresh rebuild each run
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION, embedding_function=ef, metadata={"hnsw:space": "cosine"}
    )

    print(f"[indexer] embedding = {ef_label}")
    print(f"[indexer] chroma db  = {DB_DIR}  (collection '{COLLECTION}')")

    per_file = {}
    grand_total = 0
    batch = []  # (id, text, meta)

    for path in docx_files:
        doc = Document(path)
        lines = list(extract_document_lines(doc))
        chunks = build_chunks(lines)
        topic = infer_topic(path)
        fname = os.path.basename(path)
        added = 0
        for i, chunk in enumerate(chunks):
            batch.append((safe_id(fname, grand_total + i), chunk,
                          {"source": fname, "topic": topic}))
            added += 1
            if len(batch) >= 64:  # flush incrementally to bound memory
                collection.add(ids=[b[0] for b in batch],
                               documents=[b[1] for b in batch],
                               metadatas=[b[2] for b in batch])
                batch = []
        per_file[fname] = added
        grand_total += added
        print(f"[indexer] {fname:45s} -> {added:5d} chunks  (topic={topic}, "
              f"{len(lines)} text lines, {len(chunks)} raw chunks)")

    if batch:
        collection.add(ids=[b[0] for b in batch],
                       documents=[b[1] for b in batch],
                       metadatas=[b[2] for b in batch])

    print(f"\n[indexer] DONE. total chunks indexed: {grand_total}  "
          f"(embedding: {ef_label})")
    for fname, n in per_file.items():
        print(f"    {n:6d}  {fname}")


if __name__ == "__main__":
    main()
