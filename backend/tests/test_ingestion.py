import pytest

from backend.app.services.rag.chunker import chunk_case, chunk_text


def test_empty_text_produces_no_chunks():
    assert chunk_text("   ") == []


def test_chunk_text_overlaps_and_preserves_content():
    text = "alpha " * 120
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(piece for piece, _, _ in chunks)
    assert chunks[0][1] == 0
    assert chunks[-1][2] == len(text.strip())
    assert any(first[2] > second[1] for first, second in zip(chunks, chunks[1:]))


def test_invalid_overlap_is_rejected():
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("some text", chunk_size=10, overlap=10)


def test_chunk_case_carries_metadata_and_positions():
    case = {
        "case_number": "80343",
        "case_index": 2,
        "volume": 15,
        "legal_category": "contract",
        "page_range": "1-2",
        "context": "A legal decision with enough text for one chunk.",
    }
    chunks = chunk_case(case, chunk_size=800, overlap=100)
    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "80343_0"
    assert chunks[0]["legal_category"] == "contract"
    assert chunks[0]["char_start"] == 0
