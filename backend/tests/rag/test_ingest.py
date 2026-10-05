"""Chunking test (no model, no Weaviate)."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from app.rag.ingest import load_knowledge  

SAMPLE = BACKEND.parent / "knowledge" / "sample"


def test_chunking():
    chunks = load_knowledge(SAMPLE)
    for c in chunks:
        print(f"{c.id:65} {len(c.text.split()):4} words")

    ids = [c.id for c in chunks]
    assert len(chunks) == 16
    assert "club#adhesion-au-club" in ids
    assert "projects/jarvis#team" in ids
    assert len(ids) == len(set(ids)), "duplicate ids"
    print(f"\nOK: {len(chunks)} chunks")


if __name__ == "__main__":
    test_chunking()
