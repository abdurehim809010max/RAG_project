from backend.app.services.rag.embeddings import EmbeddingClient
from backend.app.services.rag.vector_store import ChromaVectorStore


class FakeEmbeddingModel:
    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append((texts, kwargs))
        return [[index] for index, _ in enumerate(texts)]


class FakeCollection:
    def __init__(self):
        self.add_calls = []
        self.query_calls = []

    def add(self, **kwargs):
        self.add_calls.append(kwargs)

    def query(self, **kwargs):
        self.query_calls.append(kwargs)
        return {"ids": [["chunk-1"]]}

    def count(self):
        return 1


class FakeClient:
    def __init__(self, collection):
        self.collection = collection
        self.deleted = []

    def delete_collection(self, name):
        self.deleted.append(name)

    def get_or_create_collection(self, name, metadata):
        return self.collection


def test_embedding_client_adds_model_specific_prefixes():
    embedder = EmbeddingClient.__new__(EmbeddingClient)
    embedder._model = FakeEmbeddingModel()

    embedder.embed_passages(["one", "two"], batch_size=4)
    embedder.embed_queries(["question"], batch_size=2)
    embedder.embed_query("single")

    calls = embedder._model.calls
    assert calls[0][0] == ["passage: one", "passage: two"]
    assert calls[0][1]["batch_size"] == 4
    assert calls[1][0] == ["query: question"]
    assert calls[2][0] == ["query: single"]


def test_vector_store_translates_chunks_and_queries():
    collection = FakeCollection()
    store = ChromaVectorStore.__new__(ChromaVectorStore)
    store.collection = collection
    store.collection_name = "test"

    chunks = [{
        "chunk_id": "chunk-1",
        "text": "decision text",
        "case_index": 1,
        "case_number": "80343",
        "volume": 15,
        "legal_category": "contract",
        "page_range": "1-2",
        "chunk_index": 0,
        "num_chunks": 1,
    }]
    store.add_chunks(chunks, [[0.1, 0.2]])
    result = store.query([0.1, 0.2], top_k=1, where={"volume": 15})

    assert collection.add_calls[0]["ids"] == ["chunk-1"]
    assert collection.add_calls[0]["documents"] == ["decision text"]
    assert collection.query_calls[0]["query_embeddings"] == [[0.1, 0.2]]
    assert collection.query_calls[0]["n_results"] == 1
    assert result == {"ids": [["chunk-1"]]}


def test_vector_store_reset_and_count():
    collection = FakeCollection()
    store = ChromaVectorStore.__new__(ChromaVectorStore)
    store.collection = collection
    store.collection_name = "test"
    store.client = FakeClient(collection)

    store.reset()

    assert store.client.deleted == ["test"]
    assert store.count() == 1
