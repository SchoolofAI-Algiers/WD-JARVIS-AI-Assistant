"""RAG settings, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

try:  
    from dotenv import load_dotenv

    load_dotenv()
except ImportError: 
    pass


REPO_ROOT = Path(__file__).resolve().parents[3]


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class RAGSettings:
    # ------è---- Weaviate ------------------------------------------------
    weaviate_mode: str = "cloud"  
    weaviate_url: str | None = None  
    weaviate_api_key: str | None = None
    weaviate_host: str = "localhost" 
    weaviate_port: int = 8080
    weaviate_grpc_port: int = 50051
    collection: str = "SoaiChunk"

    # --- Embeddings -----------------------------------------------------
    embedding_model: str = "google/embeddinggemma-300m"
    embedding_dim: int = 768  # 768 / 512 / 256 / 128 for EmbeddingGemma
    embedding_device: str = "cpu"
    hf_token: str | None = None


    # --- Knowledge base -------------------------------------------------
    knowledge_dir: Path = field(default_factory=lambda: REPO_ROOT / "knowledge" / "processed")
    max_chunk_words: int = 300

    @classmethod
    def from_env(cls) -> "RAGSettings":
        d = cls()
        return cls(
            weaviate_mode=(_env("WEAVIATE_MODE") or d.weaviate_mode).lower(),
            weaviate_url=_env("WEAVIATE_URL"),
            weaviate_api_key=_env("WEAVIATE_API_KEY"),
            weaviate_host=_env("WEAVIATE_HOST", d.weaviate_host) or d.weaviate_host,
            weaviate_port=int(_env("WEAVIATE_PORT", str(d.weaviate_port)) or str(d.weaviate_port)),
            weaviate_grpc_port=int(_env("WEAVIATE_GRPC_PORT", str(d.weaviate_grpc_port)) or str(d.weaviate_grpc_port)),
            collection=_env("RAG_COLLECTION", d.collection) or d.collection,
            embedding_model=_env("RAG_EMBEDDING_MODEL", d.embedding_model) or d.embedding_model,
            embedding_dim=int(_env("RAG_EMBEDDING_DIM", str(d.embedding_dim)) or str(d.embedding_dim)),
            embedding_device=_env("RAG_EMBEDDING_DEVICE", d.embedding_device) or d.embedding_device,
            hf_token=_env("HF_TOKEN"),
            knowledge_dir=Path(_env("RAG_KNOWLEDGE_DIR", str(d.knowledge_dir)) or str(d.knowledge_dir)),
            max_chunk_words=int(_env("RAG_MAX_CHUNK_WORDS", str(d.max_chunk_words)) or str(d.max_chunk_words)),
        )


@lru_cache(maxsize=1)
def get_settings() -> RAGSettings:
    return RAGSettings.from_env()
