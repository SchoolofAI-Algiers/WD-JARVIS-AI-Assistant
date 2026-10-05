"""Embedding test: EmbeddingGemma loads and understands FR / EN / AR """
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.rag.config import get_settings 
from app.rag.embeddings import build_embedder  
from app.rag.models import Chunk  

JOIN = Chunk(id="a", title="Club SOAI", section="Adhésion", source="test",
             text="Pour rejoindre le club, il faut remplir le formulaire d'inscription.")
OTHER = Chunk(id="b", title="Club SOAI", section="Hackathon", source="test",
              text="Le hackathon annuel dure 48 heures.")
QUESTIONS = ["Comment rejoindre le club ?", "How can I join the club?", "كيف يمكنني الانضمام إلى النادي؟", "What is the process to become a member of the club?"]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def test_embeddings():
    embedder = build_embedder(get_settings())
    join_vec, other_vec = embedder.embed_documents([JOIN, OTHER])
    print(f"model: {embedder.name}, vector size: {embedder.dim}")
    assert len(join_vec) == embedder.dim
    print("hi")
    for question in QUESTIONS:
        q = embedder.embed_queries([question])[0]
        good, bad = dot(q, join_vec), dot(q, other_vec)
        print(f"{question:40} membership={good:.3f}  hackathon={bad:.3f}")
        assert good > bad, f"wrong chunk is closer for: {question}"
    print("\nOK: the right chunk is closest in all 3 languages")


if __name__ == "__main__":
    test_embeddings()
