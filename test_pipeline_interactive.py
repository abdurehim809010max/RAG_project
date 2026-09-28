"""
test_pipeline_interactive.py

Interactive loop: loads the embedder / vector store / pipeline ONCE, then
asks for a question in the terminal, over and over, until you type 'exit'.

Start each question with the volume and case number:

    በቅጽ 15፣ መዝገብ ቁጥር 80343 በውሳኔው ውስጥ የተገለጸ ዋና የሕግ መርህ ምን ነበር?

The retriever reads that prefix and searches only inside that case. A
question with no prefix is searched across every case.

Usage (from the project root):
    python test_pipeline_interactive.py
"""

import argparse

from backend.app.services.rag.embeddings import EmbeddingClient
from backend.app.services.rag.vector_store import ChromaVectorStore
from backend.app.services.rag.retriever import Retriever
from backend.app.services.rag.pipeline import DEFAULT_MODEL, RagPipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", default="backend/data/vector_db")
    parser.add_argument("--collection", default="volume_15")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    print("Loading embedder + vector store (one-time)...")
    embedder = EmbeddingClient()
    store = ChromaVectorStore(db_dir=args.db_dir, collection_name=args.collection)
    print(f"  -> vector store has {store.count()} chunks\n")

    pipeline = RagPipeline(Retriever(embedder, store), model_name=args.model)

    print("Ready. Start your question with: በቅጽ 15፣ መዝገብ ቁጥር <number>")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            question = input("ጥያቄዎን ያስገቡ: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            print("Exiting.")
            break

        try:
            result = pipeline.answer(question, top_k=args.top_k)
        except Exception as e:
            print(f"\n[Error] Request failed: {e}")
            print("Please try asking again.\n")
            continue

        print(f"\nGenerated answer:\n  {result['answer']}")
        print("\nSources retrieved:")
        if not result["sources"]:
            print("  (none)")
        for src in result["sources"]:
            print(f"  case {src['case_number']} ({src['page_range']}) "
                  f"distance={src['distance']:.4f}")
        print()


if __name__ == "__main__":
    main()