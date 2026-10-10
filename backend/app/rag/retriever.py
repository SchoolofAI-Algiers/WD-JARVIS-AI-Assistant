"""Retrieval: question -> most relevant SOAI chunks, or [] if nothing is relevant."""
from __future__ import annotations

from functools import lru_cache

from app.rag.config import RAGSettings, get_settings
from app.rag.embeddings import Embedder, build_embedder
from app.rag.models import RetrievedChunk
from app.rag.vector_store import WeaviateStore, build_store

NO_INFO = ("No relevant SOAI information was found. "
           "Tell the user you don't have this information; do not invent it.")


class Retriever:
    def __init__(self, embedder: Embedder, store: WeaviateStore, settings: RAGSettings):
        self.embedder = embedder
        self.store = store
        self.settings = settings

    def retrieve(self, question: str, original_question: str | None = None) -> list[RetrievedChunk]:
        """
        question: the (rewritten) question, ideally in the knowledge base language
        original_question: optional, the user's own wording/language (multilingual safety net)
        """
        queries = [q.strip() for q in (question, original_question) if q and q.strip()]
        if not queries:
            return []

        vectors = self.embedder.embed_queries(queries)
        best: dict[str, RetrievedChunk] = {}
        for query, query_vector in zip(queries, vectors):
            # 1. hybrid search gives candidates (keywords help with names / acronyms)
            hits = self.store.search(query, query_vector, limit=self.settings.top_k * 3,
                                     alpha=self.settings.alpha)
            for chunk, chunk_vector in hits:
                # 2. cosine similarity = how close in meaning (vectors are normalized)
                similarity = sum(a * b for a, b in zip(query_vector, chunk_vector))
                if chunk.id not in best or similarity > best[chunk.id].similarity:
                    best[chunk.id] = RetrievedChunk(**chunk.model_dump(), similarity=similarity)

        # 3. keep only relevant chunks, most similar first
        relevant = [c for c in best.values() if c.similarity >= self.settings.min_similarity]
        relevant.sort(key=lambda c: c.similarity, reverse=True)
        return relevant[: self.settings.top_k]


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Text to put in the LLM prompt: numbered passages, or the 'no info' message."""
    if not chunks:
        return NO_INFO
    return "\n\n".join(f"[{i}] {c.heading} (source: {c.source})\n{c.text}"
                       for i, c in enumerate(chunks, start=1))


def get_sources(chunks: list[RetrievedChunk]) -> list[dict]:
    """Sources for the API / frontend."""
    return [{"id": c.id, "title": c.title, "section": c.section, "source": c.source,
             "similarity": round(c.similarity, 3)} for c in chunks]


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    """One shared retriever, so the embedding model is loaded only once."""
    settings = get_settings()
    return Retriever(build_embedder(settings), build_store(settings), settings)


def retrieve(question: str, original_question: str | None = None) -> list[RetrievedChunk]:
    """Shortcut for the rest of the backend: `from app.rag import retrieve`."""
    return get_retriever().retrieve(question, original_question)
