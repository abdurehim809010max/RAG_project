from backend.app.services.rag.retriever import Retriever
from backend.app.services.rag.chunker import chunk_text


class FakeEmbedder:
    def embed_query(self, text):
        return [len(text)]


class FakeStore:
    def __init__(self, results=None):
        self.calls = []
        self.results = results or {
            "ids": [["chunk-1"]],
            "documents": [["decision text"]],
            "metadatas": [[{
                "case_number": "80343",
                "volume": 15,
                "legal_category": "contract",
                "page_range": "1-2",
            }]],
            "distances": [[0.12]],
        }

    def query(self, embedding, top_k=5, where=None):
        self.calls.append((embedding, top_k, where))
        return self.results


def test_chunking_respects_size_and_overlap():
    chunks = chunk_text("x" * 120, chunk_size=40, overlap=10)

    assert [len(chunk[0]) for chunk in chunks] == [40, 40, 40, 30]
    assert chunks[0][2] - chunks[1][1] == 10
    assert chunks[1][2] - chunks[2][1] == 10


def test_retrieve_returns_top_k_in_store_order():
    store = FakeStore(results={
        "ids": [["best", "second"]],
        "documents": [["best text", "second text"]],
        "metadatas": [[
            {"case_number": "80343", "page_range": "1", "legal_category": "tax"},
            {"case_number": "80343", "page_range": "2", "legal_category": "tax"},
        ]],
        "distances": [[0.1, 0.4]],
    })
    retriever = Retriever(FakeEmbedder(), store)

    result = retriever.retrieve("legal principle", top_k=2, auto_filter_case_number=False)

    assert [chunk["chunk_id"] for chunk in result] == ["best", "second"]
    assert [chunk["distance"] for chunk in result] == [0.1, 0.4]
    assert store.calls[0][1] == 2


def test_retrieve_handles_empty_results():
    store = FakeStore(results={
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    })
    retriever = Retriever(FakeEmbedder(), store)

    assert retriever.retrieve("nothing here", auto_filter_case_number=False) == []


def test_parse_scope_removes_strict_case_prefix():
    retriever = Retriever(FakeEmbedder(), FakeStore())
    scope = retriever.parse_scope("በቅጽ 15፣ መዝገብ ቁጥር 80343፣ ዋና መርህ")
    assert scope == {
        "volume": 15,
        "case_number": "80343",
        "search_text": "ዋና መርህ",
        "strict": True,
    }


def test_retrieve_uses_case_and_volume_filters():
    store = FakeStore()
    retriever = Retriever(FakeEmbedder(), store)
    result = retriever.retrieve("በቅጽ 15 መዝገብ ቁጥር 80343 ዋና መርህ", top_k=3)
    assert result[0]["chunk_id"] == "chunk-1"
    assert store.calls[0][1] == 3
    assert store.calls[0][2] == {"$and": [{"volume": 15}, {"case_number": "80343"}]}


def test_explicit_scope_overrides_query_scope():
    store = FakeStore()
    retriever = Retriever(FakeEmbedder(), store)
    retriever.retrieve("question", case_number="99999", volume=4, legal_category="tax")
    assert store.calls[0][2] == {
        "$and": [{"legal_category": "tax"}, {"volume": 4}, {"case_number": "99999"}]
    }
