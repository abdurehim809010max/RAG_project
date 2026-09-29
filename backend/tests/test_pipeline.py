from backend.app.services.rag.pipeline import RagPipeline, build_prompt


class FakeRetriever:
    def retrieve(self, *args, **kwargs):
        return [{
            "case_number": "80343",
            "page_range": "1-2",
            "legal_category": "contract",
            "chunk_id": "80343_0",
            "distance": 0.2,
            "text": "A decision excerpt.",
        }]


def test_build_prompt_contains_query_and_context():
    prompt = build_prompt("What is the principle?", [{
        "case_number": "80343",
        "page_range": "1-2",
        "text": "A decision excerpt.",
    }])
    assert "What is the principle?" in prompt
    assert "A decision excerpt." in prompt
    assert "80343" in prompt


def test_answer_returns_sources_without_calling_llm_for_empty_results():
    pipeline = RagPipeline.__new__(RagPipeline)
    pipeline.retriever = type("EmptyRetriever", (), {"retrieve": lambda self, *a, **k: []})()
    assert pipeline.answer("question") == {
        "answer": "ተዛማጅ የፍርድ ውሳኔ አላገኘሁም።",
        "sources": [],
    }


def test_answer_maps_generated_text_to_sources():
    pipeline = RagPipeline.__new__(RagPipeline)
    pipeline.retriever = FakeRetriever()
    pipeline._generate_with_retry = lambda prompt: "grounded answer"
    result = pipeline.answer("question")
    assert result["answer"] == "grounded answer"
    assert result["sources"][0]["chunk_id"] == "80343_0"
