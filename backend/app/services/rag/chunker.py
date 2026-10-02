"""
RAG/chunker.py

Splits case text into overlapping fixed-size chunks for embedding.
Pure functions only — no file I/O, no CLI — so pipeline.py and any
future ingestion endpoint can import and call this directly.
"""

import re

# Prefer to break at these, in priority order, when nudging a cut point. 
# Amharic full-stop is ፡፡ (two dots); newline and space are fallbacks.
_BREAK_PRIORITY = ["፡፡",".","፣", "።", "!", "?", ",", "\n\n", "\n", " "]

DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 150


def _find_nearby_break(text: str, target_idx: int, search_window: int = 80) -> int:
    """
    Look for a good place to cut `text` near `target_idx`, preferring
    sentence-ending punctuation, then newlines, then a plain space, within
    `search_window` characters on either side. Falls back to target_idx
    itself (a hard cut) if nothing better is found nearby.
    """
    if target_idx <= 0:
        return 0
    if target_idx >= len(text):
        return len(text)

    lo = max(0, target_idx - search_window)
    hi = min(len(text), target_idx + search_window)
    window = text[lo:hi]

    for marker in _BREAK_PRIORITY:
        fwd = window.find(marker, target_idx - lo)
        if fwd != -1:
            return lo + fwd + len(marker)
        bwd = window.rfind(marker, 0, target_idx - lo)
        if bwd != -1:
            return lo + bwd + len(marker)

    return target_idx


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE,
               overlap: int = DEFAULT_OVERLAP):
    """
    Split `text` into overlapping windows of ~chunk_size characters,
    snapped to nearby sentence/whitespace boundaries so words never get
    sliced in half at a chunk edge.

    Returns a list of (chunk_text, char_start, char_end) tuples.
    """
    text = text.strip()
    n = len(text)
    if n == 0:
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    while start < n:
        target_end = start + chunk_size
        if target_end >= n:
            end = n
        else:
            end = _find_nearby_break(text, target_end)
            if end <= start:
                end = min(n, target_end)

        piece = text[start:end].strip()
        if piece:
            chunks.append((piece, start, end))

        if end >= n:
            break

        next_start = end - overlap
        start = max(next_start, start + 1)  # guarantee forward progress

    return chunks


def chunk_case(case: dict, chunk_size: int = DEFAULT_CHUNK_SIZE,
               overlap: int = DEFAULT_OVERLAP) -> list[dict]:
    """
    Chunk a single case record (as loaded from a case_<idx>_<num>.json
    file) into a list of chunk records ready for embedding, each carrying
    the case's metadata plus its own position.
    """
    pieces = chunk_text(case.get("context", ""), chunk_size=chunk_size, overlap=overlap)

    records = []
    for i, (text, start, end) in enumerate(pieces):
        records.append({
            "chunk_id": f"{case['case_number']}_{i}",
            "case_index": case["case_index"],
            "case_number": case["case_number"],
            "volume": case["volume"],
            "legal_category": case["legal_category"],
            "page_range": case["page_range"],
            "chunk_index": i,
            "num_chunks": len(pieces),
            "char_start": start,
            "char_end": end,
            "text": text,
        })
    return records
