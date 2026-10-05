from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from app.rag.models import Chunk

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def dim(self) -> int: ...

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_documents(self, chunks: Sequence[Chunk]) -> list[list[float]]: ...

@dataclass(frozen=True)
class EncodingPreset:
    """How a given model expects queries and documents to be formatted."""
    query_prompt: str = "" 
    doc_template: str = "{heading}\n{text}" 
    encode_kwargs: tuple[tuple[str, Any], ...] = ()  
    query_kwargs: tuple[tuple[str, Any], ...] = ()
    doc_kwargs: tuple[tuple[str, Any], ...] = ()
    trust_remote_code: bool = False


PRESETS: dict[str, EncodingPreset] = {
    "embeddinggemma": EncodingPreset(
        query_prompt="task: search result | query: ",
        doc_template="title: {heading} | text: {text}",
    ),
    #we can switch to another model easily
}


def preset_for(model_name: str) -> EncodingPreset:
    lowered = model_name.lower()
    for key, preset in PRESETS.items():
        if key in lowered:
            return preset
    logger.warning("No encoding preset for %s, using plain text (check the model card!)", model_name)
    return EncodingPreset()


class SentenceTransformerEmbedder:
    """Lazy-loaded sentence-transformers model (loaded once, on first use)."""

    def __init__(self, model_name: str, dim: int | None = None, device: str = "cpu",
                 hf_token: str | None = None, model=None):
        self.name = model_name
        self.preset = preset_for(model_name)
        self._dim = dim
        self._device = device
        self._token = hf_token
        self._model = model 
        self._lock = threading.Lock()

    @property
    def model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer
                    logger.info("Loading embedding model %s ...", self.name)
                    self._model = SentenceTransformer(
                        self.name,
                        device=self._device,
                        token=self._token,
                        truncate_dim=self._dim,
                        trust_remote_code=self.preset.trust_remote_code,
                    )
        return self._model

    @property
    def dim(self) -> int:
        """Actual vector size"""
        model = self.model
        get_dim = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
        native = get_dim()
        if native is not None:
            native_dim = int(native)
            if self._dim is None:
                self._dim = native_dim
            else:
                self._dim = min(self._dim, native_dim)
        if self._dim is None:
            raise ValueError(f"Embedding dimension is unavailable for model {self.name!r}.")
        return int(self._dim)

    def _encode(self, texts: list[str], extra: tuple[tuple[str, Any], ...]) -> list[list[float]]:
        kwargs: dict[str, Any] = dict(self.preset.encode_kwargs) | dict(extra)
        kwargs.setdefault("prompt", "") 
        vectors = self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True,
                                    show_progress_bar=False, **kwargs)
        return [v.astype(float).tolist() for v in vectors]

    def format_query(self, text: str) -> str:
        return f"{self.preset.query_prompt}{text}" if self.preset.query_prompt else text

    def format_document(self, chunk: Chunk) -> str:
        return self.preset.doc_template.format(heading=chunk.heading, text=chunk.text.strip())

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode([self.format_query(t) for t in texts], self.preset.query_kwargs)

    def embed_documents(self, chunks: Sequence[Chunk]) -> list[list[float]]:
        return self._encode([self.format_document(c) for c in chunks], self.preset.doc_kwargs)


def build_embedder(settings) -> Embedder:
    return SentenceTransformerEmbedder(
        settings.embedding_model,
        dim=settings.embedding_dim,
        device=settings.embedding_device,
        hf_token=settings.hf_token,
    )