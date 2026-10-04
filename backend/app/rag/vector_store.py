"""Vector store: Weaviate."""
from __future__ import annotations

import logging
from typing import Iterable, Sequence, cast

from app.rag.models import Chunk

logger = logging.getLogger(__name__)


def _collection_signature(model_name: str, dim: int) -> str:
    return f"SOAI knowledge chunks | embedding_model={model_name} | dim={dim}"


def _chunk_to_props(chunk: Chunk) -> dict:
    return {
        "chunk_id": chunk.id,
        "text": chunk.text,
        "title": chunk.title,
        "section": chunk.section or "",
        "source": chunk.source,
        "category": chunk.category or "",
        "lang": chunk.lang or "",
        "updated": chunk.updated or "",
        "doc_path": chunk.doc_path,
    }


class WeaviateStore:
    def __init__(self, settings, client=None):
        self.settings = settings
        self._client = client

    # ------- connection ---------------------------------------------------------
    @property
    def client(self):
        if self._client is None:
            self._client = self._connect()
        return self._client

    def _connect(self):
        import weaviate
        from weaviate.classes.init import AdditionalConfig, Auth, Timeout

        s = self.settings
        extra = AdditionalConfig(timeout=Timeout(init=15, query=20, insert=120))
        if s.weaviate_mode == "local":
            auth = Auth.api_key(s.weaviate_api_key) if s.weaviate_api_key else None
            return weaviate.connect_to_local(host=s.weaviate_host, port=s.weaviate_port,
                                             grpc_port=s.weaviate_grpc_port, auth_credentials=auth,
                                             additional_config=extra)
        if not s.weaviate_url or not s.weaviate_api_key:
            raise RuntimeError("WEAVIATE_URL and WEAVIATE_API_KEY must be set (or WEAVIATE_MODE=local)")
        return weaviate.connect_to_weaviate_cloud(cluster_url=s.weaviate_url,
                                                  auth_credentials=Auth.api_key(s.weaviate_api_key),
                                                  additional_config=extra)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @property
    def collection(self):
        return self.client.collections.get(self.settings.collection)

    # -------- schema -------------------------------------------------------------
    def ensure_collection(self, dim: int, model_name: str, reset: bool = False) -> None:
        from weaviate.classes.config import Configure, DataType, Property, Tokenization, VectorDistances

        name = self.settings.collection
        signature = _collection_signature(model_name, dim)
        if reset and self.client.collections.exists(name):
            logger.warning("Deleting collection %s", name)
            self.client.collections.delete(name)

        if self.client.collections.exists(name):
            current = self.client.collections.get(name).config.get().description or ""
            if current != signature:
                raise RuntimeError(
                    f"Collection {name!r} was built with a different embedding setup:\n"
                    f"  stored : {current}\n  current: {signature}\n"
                    "Re-index with `python -m app.rag.ingest --reset`."
                )
            return

        def keyword(n: str) -> Property:  # exact-match field, not used by BM25
            return Property(name=n, data_type=DataType.TEXT, tokenization=Tokenization.FIELD,
                            index_searchable=False, index_filterable=True)

        def searchable(n: str) -> Property:  # used by BM25
            return Property(name=n, data_type=DataType.TEXT, tokenization=Tokenization.WORD,
                            index_searchable=True)

        self.client.collections.create(
            name,
            description=signature,
            vector_config=Configure.Vectors.self_provided(
                vector_index_config=Configure.VectorIndex.flat(distance_metric=VectorDistances.COSINE),
            ),
            properties=[
                keyword("chunk_id"),
                searchable("title"),
                searchable("section"),
                searchable("text"),
                keyword("source"),
                keyword("category"),
                keyword("lang"),
                keyword("updated"),
                keyword("doc_path"),
            ],
        )
        logger.info("Created collection %s (%s)", name, signature)

    # ------ writes -------------------------------------------------------------
    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> int:
        from weaviate.util import generate_uuid5

        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        col = self.collection
        with col.batch.fixed_size(batch_size=64) as batch:
            for chunk, vec in zip(chunks, vectors):
                batch.add_object(properties=_chunk_to_props(chunk), uuid=generate_uuid5(chunk.id),
                                 vector=list(vec))
        failed = col.batch.failed_objects
        if failed:
            raise RuntimeError(f"{len(failed)} chunks failed to upload, first error: {failed[0].message}")
        return len(chunks)

    def delete_except(self, keep_ids: Iterable[str]) -> int:
        """Remove chunks that no longer exist in knowledge/processed."""
        keep = set(keep_ids)
        col = self.collection
        stale = [obj.uuid for obj in col.iterator(return_properties=["chunk_id"])
                 if obj.properties.get("chunk_id") not in keep]
        for uid in stale:
            col.data.delete_by_id(uid)
        return len(stale)

    # ------ reads -------------------------------------------------------------
    def search(self, query: str, vector: list[float], limit: int,
               alpha: float) -> list[tuple[Chunk, list[float]]]:
        """Hybrid search (keywords + meaning). Returns (chunk, stored vector) pairs."""
        from weaviate.classes.query import HybridFusion

        res = self.collection.query.hybrid(
            query=query,
            vector=vector,
            alpha=alpha,
            limit=limit,
            fusion_type=HybridFusion.RELATIVE_SCORE,
            query_properties=["title^2", "section^2", "text"],  # titles count double for keywords
            include_vector=True,
        )
        results = []
        for obj in res.objects:
            p = dict(obj.properties)
            chunk = Chunk(
                id=str(p["chunk_id"]),
                text=str(p.get("text") or ""),
                title=str(p.get("title") or ""),
                section=str(p.get("section") or "") or None,
                source=str(p.get("source") or ""),
                category=str(p.get("category") or "") or None,
                lang=str(p.get("lang") or "") or None,
                updated=str(p.get("updated") or "") or None,
                doc_path=str(p.get("doc_path") or ""),
            )
            stored_vector = cast(list[float], obj.vector["default"])
            results.append((chunk, list(stored_vector)))
        return results

    def count(self) -> int:
        return int(self.collection.aggregate.over_all(total_count=True).total_count or 0)


def build_store(settings) -> WeaviateStore:
    return WeaviateStore(settings)