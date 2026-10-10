"""Chunking test on the real knowledge base (no model, no Weaviate)."""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

from app.rag.ingest import load_knowledge  

KB = BACKEND.parent / "knowledge" / "processed"


def test_chunking():
    chunks = load_knowledge(KB)
    for c in chunks:
        print(f"{c.id:75} {len(c.text.split()):4} words")
    print(f"\n{len(chunks)} chunks from {len({c.doc_path for c in chunks})} files")

    ids = [c.id for c in chunks]
    assert chunks, "no chunks found"
    assert len(ids) == len(set(ids)), "duplicate chunk ids"
    too_short = [c.id for c in chunks if len(c.text.split()) < 15]
    too_long = [c.id for c in chunks if len(c.text.split()) > 300]
    assert not too_short, f"chunks too short (merge or remove them): {too_short}"
    assert not too_long, f"chunks too long (split them): {too_long}"
    assert not [c.id for c in chunks if "title:" in c.text], "front matter leaked into a chunk"
    print("OK")


if __name__ == "__main__":
    test_chunking()
