"""
backend/app/services/rag/retriever.py

Similarity search over the vector store.

Scoping a question to one case
------------------------------
Users start a question with the volume and case number:

    "በቅጽ 15፣ መዝገብ ቁጥር 80343 በውሳኔው ውስጥ የተገለጸ ዋና የሕግ መርህ ምን ነበር?"

The retriever reads that prefix, filters the search to that volume/case
(an exact metadata lookup), and embeds only the rest of the question.
Embedding models represent numbers poorly, so the number is used as a
filter and not as search text.

If the case named in the prefix isn't in the index, the result is EMPTY on
purpose — silently answering from unrelated cases would be worse than
saying nothing.

Fallbacks, in order:
  1. Explicit case_number / volume arguments (from an API field, etc.)
  2. The "በቅጽ N፣ መዝገብ ቁጥር N" prefix (strict, as above)
  3. Loose guess: any 4-6 digit number in the text (lenient — if it matches
     no case it is ignored and a plain semantic search runs)
  4. No number at all -> plain semantic search across everything

Still missing: hybrid (keyword + vector) search and a reranker; `rerank` is
a placeholder so the signature won't change when they arrive.
"""

import re

from .embeddings import EmbeddingClient
from .vector_store import ChromaVectorStore

# "በቅጽ 15፣ መዝገብ ቁጥር 80343" at the start of the question
_PREFIX_RE = re.compile(
    r"^\s*በቅጽ\s*(\d{1,3})\s*[፣,፡]?\s*መዝገብ\s*ቁጥር\s*(\d{4,6})\s*[፣,፡]?\s*"
)
_VOLUME_RE = re.compile(r"ቅጽ\s*(\d{1,3})")
_CASE_ANY_RE = re.compile(r"\b(\d{4,6})\b")


class Retriever:
    def __init__(self, embedder: EmbeddingClient, vector_store: ChromaVectorStore):
        self.embedder = embedder
        self.vector_store = vector_store

    def parse_scope(self, query: str) -> dict:
        """
        Work out which volume/case a question is about.

        Returns {volume, case_number, search_text, strict}:
          search_text - what to embed (prefix removed when one was found)
          strict      - True when the scope came from the proper prefix, so
                        "no such case" must return nothing rather than fall
                        back to unfiltered search.
        """
        m = _PREFIX_RE.match(query)
        if m:
            rest = query[m.end():].strip()
            return {
                "volume": int(m.group(1)),
                "case_number": m.group(2),
                "search_text": rest or query,
                "strict": True,
            }

        vm = _VOLUME_RE.search(query)
        cm = _CASE_ANY_RE.search(query)
        return {
            "volume": int(vm.group(1)) if vm else None,
            "case_number": cm.group(1) if cm else None,
            "search_text": query,
            "strict": False,
        }

    def retrieve(self, query: str, top_k: int = 5,
                 case_number: str | None = None,
                 volume: int | None = None,
                 legal_category: str | None = None,
                 auto_filter_case_number: bool = True,
                 rerank: bool = False) -> list[dict]:
        """
        Return the top_k most relevant chunks for `query`, best first:
            {chunk_id, text, distance, case_number, legal_category,
             page_range, case_index, chunk_index, num_chunks, volume}

        case_number / volume: explicit scope; overrides anything parsed
        from the question text.

        auto_filter_case_number: set False to skip all parsing and run pure
        semantic search on the raw question (useful for retrieval evals).

        legal_category: optional extra metadata filter.
        rerank: NOT YET IMPLEMENTED; raises so it can't silently no-op.
        """
        if rerank:
            raise NotImplementedError(
                "Reranking isn't built yet — call with rerank=False."
            )

        explicit_case = case_number is not None  # caller stated it -> trust it

        search_text = query
        strict = explicit_case
        if auto_filter_case_number:
            scope = self.parse_scope(query)
            search_text = scope["search_text"]
            strict = strict or scope["strict"]
            if case_number is None:
                case_number = scope["case_number"]
            if volume is None:
                volume = scope["volume"]

        query_embedding = self.embedder.embed_query(search_text)

        base_filters = []
        if legal_category:
            base_filters.append({"legal_category": legal_category})
        if volume is not None:
            base_filters.append({"volume": volume})

        if case_number:
            where = self._combine(base_filters + [{"case_number": case_number}])
            results = self._run_query(query_embedding, top_k, where)
            if results or strict:
                # strict: the user named this case, so "not found" is the
                # honest answer — don't substitute other cases.
                return results
            # lenient guess (a stray number in the text) matched no case:
            # ignore it and fall through to plain semantic search.

        return self._run_query(query_embedding, top_k, self._combine(base_filters))

    @staticmethod
    def _combine(filters: list[dict]) -> dict | None:
        if not filters:
            return None
        return filters[0] if len(filters) == 1 else {"$and": filters}

    def _run_query(self, query_embedding, top_k, where) -> list[dict]:
        raw = self.vector_store.query(query_embedding, top_k=top_k, where=where)
        results = []
        for chunk_id, text, metadata, distance in zip(
            raw["ids"][0], raw["documents"][0], raw["metadatas"][0], raw["distances"][0]
        ):
            results.append({
                "chunk_id": chunk_id,
                "text": text,
                "distance": distance,
                **metadata,
            })
        return results
