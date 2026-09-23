"""Embedding backends behind one small interface.

Anything that satisfies `Embedder` can be indexed and queried. Two things are
part of the interface beyond `embed()`, because both are what make swapping a
backend safe rather than merely possible:

- `max_input_tokens` / `count_tokens`: the chunker sizes chunks from the
  embedder's own limit and tokenizer, so a model with a 512-token window
  gets bigger chunks automatically and nothing is silently truncated.
- `name`: recorded in the index, so vectors from one model are never
  compared against vectors from another (see store.EmbedderMismatchError).
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, runtime_checkable

from meridian.config import Settings


@runtime_checkable
class Embedder(Protocol):
    name: str
    dimension: int
    max_input_tokens: int

    def count_tokens(self, text: str) -> int: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Local sentence-transformers model. Needs `pip install -e ".[local-embeddings]"`."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "SentenceTransformerEmbedder needs sentence-transformers: "
                'pip install -e ".[local-embeddings]" (or set EMBEDDING_BACKEND=hashing)'
            ) from exc

        self._model = SentenceTransformer(model_name)
        self.name = model_name
        # Renamed in newer sentence-transformers; keep working on 3.x too.
        get_dimension = getattr(self._model, "get_embedding_dimension", None) or getattr(
            self._model, "get_sentence_embedding_dimension"
        )
        self.dimension = int(get_dimension())
        self.max_input_tokens = int(self._model.max_seq_length)

    def count_tokens(self, text: str) -> int:
        # Includes the special tokens, i.e. the length the model actually sees.
        return len(self._model.tokenizer(text, add_special_tokens=True)["input_ids"])

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True
        )
        return vectors.tolist()


class HashingEmbedder:
    """Dependency-free lexical baseline: signed feature hashing of word tokens.

    Deterministic and offline, which is why CI and most tests use it. It is
    NOT a semantic model -- two texts only score as similar if they share
    words -- so it's also the natural baseline to measure a real model
    against on the vocabulary-mismatch cases.
    """

    def __init__(self, dimension: int = 256, max_input_tokens: int = 256) -> None:
        self.name = f"hashing-{dimension}"
        self.dimension = dimension
        self.max_input_tokens = max_input_tokens

    @staticmethod
    def _words(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def count_tokens(self, text: str) -> int:
        # Rough word-piece estimate: tokenizers split hyphenated names and
        # rare words into several pieces, so words undercount.
        return math.ceil(len(self._words(text)) * 1.3) + 2

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for word in self._words(text):
            digest = hashlib.blake2b(word.encode(), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            sign = 1.0 if (value >> 63) & 1 else -1.0
            vector[value % self.dimension] += sign
        norm = math.sqrt(sum(x * x for x in vector))
        return [x / norm for x in vector] if norm else vector

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


def get_embedder(settings: Settings) -> Embedder:
    if settings.embedding_backend == "sentence-transformers":
        return SentenceTransformerEmbedder(settings.embedding_model)
    if settings.embedding_backend == "hashing":
        return HashingEmbedder()
    raise ValueError(f"unknown embedding backend: {settings.embedding_backend!r}")
