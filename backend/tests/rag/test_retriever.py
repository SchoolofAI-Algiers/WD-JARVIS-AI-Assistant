"""Indexing + retrieval test on knowledge/sample, using a separate Weaviate collection."""
import sys
from dataclasses import replace
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from app.rag.config import get_settings  
from app.rag.embeddings import build_embedder  
from app.rag.ingest import build_index, load_knowledge  
from app.rag.retriever import Retriever, format_context, get_sources  
from app.rag.vector_store import WeaviateStore  

SAMPLE = BACKEND.parent / "knowledge" / "sample"

KNOWN = [  # (question, original question or None, chunk that should be found)
    ("Comment devenir membre du club SOAI ?", None, "club#adhesion-au-club"),
    ("Combien de temps dure le hackathon ?", None, "events/hackathon#deroulement-du-hackathon"),
    ("Who works on the JARVIS project?", None, "projects/jarvis#team"),
    ("Quand ont lieu les ateliers hebdomadaires ?", "متى تقام الورشات الأسبوعية؟", "club#ateliers-hebdomadaires"),
]
UNKNOWN = ["Quelle est la recette du couscous ?", "Who won the football world cup in 2022?"]


def test_retriever():
    settings = replace(get_settings(), collection="SoaiChunkTest")  #test in a diff collection
    embedder = build_embedder(settings)
    print(f"Embedding finished")
    store = WeaviateStore(settings)
    print(f"Using Weaviate store")
    try:
        #indexing
        chunks = load_knowledge(SAMPLE)
        report = build_index(chunks, embedder, store, reset=True)
        print(f"indexed: {report}")
        assert report.total_in_store == len(chunks)
        again = build_index(chunks, embedder, store)
        assert again.total_in_store == len(chunks), "re-indexing created duplicates"

        #retrieval with no threshold to see all similarities
        print("\nRETRIEVAL TESTS")
        debug = Retriever(embedder, store, replace(settings, min_similarity=-1.0))
        normal = Retriever(embedder, store, settings)

        print("\nKNOWN questions")
        for question, original, expected in KNOWN:
            found = debug.retrieve(question, original)
            print(f"  {question:45} -> {found[0].id}  sim={found[0].similarity:.3f}")
            assert expected in [c.id for c in normal.retrieve(question, original)], question

        print("\nUNKNOWN questions (should return nothing)")
        for question in UNKNOWN:
            found = debug.retrieve(question)
            print(f"  {question:45} best sim={found[0].similarity:.3f}")
            assert normal.retrieve(question) == [], f"should not answer: {question}"

        result = normal.retrieve(KNOWN[0][0])
        print("\nCONTEXT FOR THE LLM:\n" + format_context(result))
        print("\nSOURCES:", get_sources(result))
        print("\nNO ANSWER:", format_context([]))
        print("\nOK")
    finally:
        store.client.collections.delete(settings.collection)
        store.close()


if __name__ == "__main__":
    test_retriever()
