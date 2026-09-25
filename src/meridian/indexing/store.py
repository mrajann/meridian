"""ChromaDB-backed vector index, persisted to disk.

Chroma is used purely as a vector + metadata store: we always compute
embeddings ourselves and pass them in, and `embedding_function=None` stops
Chroma from ever falling back to its own default model. That keeps the
embedder behind our swappable interface as the single source of vectors.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError

from meridian.indexing.chunking import Chunk
from meridian.indexing.embeddings import Embedder

COLLECTION_NAME = "meridian_corpus"


class IndexNotBuiltError(RuntimeError):
    pass


class EmbedderMismatchError(RuntimeError):
    """The index was built with a different embedder than the one querying it.
    Vectors from different models live in unrelated spaces, so comparing them
    doesn't error -- it silently returns nonsense. Fail loudly instead."""


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    text: str
    score: float  # cosine similarity, higher is closer
    metadata: dict[str, Any]

    @property
    def doc_id(self) -> str:
        return self.metadata["doc_id"]


def _batches(items: list, size: int) -> Iterator[list]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def build_filter(
    doc_type: str | list[str] | None = None,
    service: str | None = None,
    tier: str | int | list[str | int] | None = None,
) -> dict[str, Any] | None:
    """Chroma `where` clause from the filters retrieval actually uses.

    `service` matches any of a document's services (a cascade alert lists
    six). `tier` is the tier of the document's *primary* service, and is
    stored as a string ("1", "2", "3", "external", "unknown") because Chroma
    rejects `$in` over mixed int/str values.
    """
    clauses: list[dict[str, Any]] = []
    if doc_type is not None:
        clauses.append({"doc_type": {"$in": doc_type} if isinstance(doc_type, list) else doc_type})
    if service is not None:
        clauses.append({"services": {"$contains": service}})
    if tier is not None:
        clauses.append({"tier": {"$in": [str(t) for t in tier]} if isinstance(tier, list) else str(tier)})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


class VectorIndex:
    def __init__(self, path: Path, embedder: Embedder, collection_name: str = COLLECTION_NAME) -> None:
        self.embedder = embedder
        self._collection_name = collection_name
        self._client = chromadb.PersistentClient(
            path=str(path), settings=ChromaSettings(anonymized_telemetry=False)
        )

    def build(self, chunks: list[Chunk], metadatas: list[dict[str, Any]], batch_size: int = 64) -> int:
        """Full rebuild: drop the collection and re-add everything. The corpus
        is small and deterministic, so this beats tracking which chunks went
        stale, and it can't leave orphaned chunks behind."""
        if len(chunks) != len(metadatas):
            raise ValueError("chunks and metadatas must be the same length")
        try:
            self._client.delete_collection(self._collection_name)
        except NotFoundError:
            pass

        collection = self._client.create_collection(
            self._collection_name,
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
            metadata={"embedder": self.embedder.name, "dimension": self.embedder.dimension},
        )
        for batch in _batches(list(zip(chunks, metadatas)), batch_size):
            batch_chunks = [c for c, _ in batch]
            collection.add(
                ids=[c.chunk_id for c in batch_chunks],
                embeddings=self.embedder.embed([c.embed_text for c in batch_chunks]),
                documents=[c.text for c in batch_chunks],
                metadatas=[m for _, m in batch],
            )
        return collection.count()

    def _collection(self):
        try:
            collection = self._client.get_collection(self._collection_name, embedding_function=None)
        except NotFoundError as exc:
            raise IndexNotBuiltError("no index found; build it with: python -m meridian.indexing build") from exc

        built_with = (collection.metadata or {}).get("embedder")
        if built_with != self.embedder.name:
            raise EmbedderMismatchError(
                f"index was built with embedder {built_with!r} but is being queried with "
                f"{self.embedder.name!r}; rebuild the index or use the matching embedder"
            )
        return collection

    def count(self) -> int:
        return self._collection().count()

    def all_chunks(self) -> dict[str, list]:
        """ids/documents/metadatas for every indexed chunk -- the source of
        truth a keyword index is built from, so it always matches exactly
        what's in the vector index rather than re-deriving chunks separately."""
        result = self._collection().get(include=["documents", "metadatas"])
        return {"ids": result["ids"], "documents": result["documents"], "metadatas": result["metadatas"]}

    def query(self, text: str, k: int = 5, where: dict[str, Any] | None = None) -> list[Hit]:
        collection = self._collection()
        result = collection.query(
            query_embeddings=self.embedder.embed([text]),
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return [
            Hit(chunk_id=chunk_id, text=document, score=1.0 - distance, metadata=metadata)
            for chunk_id, document, metadata, distance in zip(
                result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
            )
        ]
