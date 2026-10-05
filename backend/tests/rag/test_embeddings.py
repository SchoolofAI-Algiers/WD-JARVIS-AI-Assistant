"""Embedding test on the real SOAI knowledge base (needs HF_TOKEN in .env)."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from app.rag.config import get_settings 
from app.rag.embeddings import build_embedder  
from app.rag.ingest import load_knowledge  

KB = BACKEND.parent / "knowledge" / "processed"

# (question, chunks that should be the closest) - several ids when the FAQ repeats the content
QUESTIONS = [
    ("What is the hAIck datathon?",
     ["soai_activities#haick-national-datathon", "soai_faq#what-is-haick"]),
    ("C'est quoi le datathon hAIck ?",
     ["soai_activities#haick-national-datathon", "soai_faq#what-is-haick"]),
    ("How do you ensure events organization?",
     ["soai_overview#logistics", "soai_faq#what-does-the-logistics-team-do"]),
]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def test_embeddings():
    chunks = load_knowledge(KB)
    embedder = build_embedder(get_settings())
    vectors = embedder.embed_documents(chunks)
    print(f"model: {embedder.name}, vector size: {embedder.dim}, {len(chunks)} chunks\n")

    results = []
    for question, expected in QUESTIONS:
        q = embedder.embed_queries([question])[0]
        ranked = sorted(zip(chunks, vectors), key=lambda cv: dot(q, cv[1]), reverse=True)
        ids = [c.id for c, _ in ranked]
        rank = min((ids.index(e) + 1 for e in expected if e in ids), default=None)

        if rank == 1:
            status = "OK   "
        elif rank is not None and rank <= 3:
            status = "CLOSE"  
        else:
            status = "MISS "
        results.append(status.strip())

        print(f"{status} {question}")
        print(f"      expected: {expected[0]} (rank {rank})")
        for i, (c, v) in enumerate(ranked[:3], start=1):
            print(f"      #{i} {dot(q, v):.3f}  {c.id}")
        print()

    print(f"{results.count('OK')} OK, {results.count('CLOSE')} close (top 3), "
          f"{results.count('MISS')} miss out of {len(QUESTIONS)}")


if __name__ == "__main__":
    test_embeddings()