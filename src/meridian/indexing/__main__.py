"""Build and query the vector index.

    python -m meridian.indexing build
    python -m meridian.indexing query "connection pool exhausted" --type runbook --tier 1 -k 5
"""

from __future__ import annotations

import argparse

from meridian.catalog import load_catalog
from meridian.config import settings
from meridian.corpus import load_corpus
from meridian.indexing.embeddings import get_embedder
from meridian.indexing.pipeline import build_index
from meridian.indexing.store import VectorIndex, build_filter


def _build() -> None:
    embedder = get_embedder(settings)
    index = VectorIndex(settings.chroma_persist_dir, embedder)
    stats = build_index(load_corpus(), load_catalog(), embedder, index)
    print(f"embedder: {embedder.name} (dim {embedder.dimension}, max {embedder.max_input_tokens} tokens)")
    print(f"indexed {stats.chunks} chunks from {stats.documents} documents into {settings.chroma_persist_dir}")
    print(f"chunks by type: {stats.chunks_by_type}")
    print(f"longest embedded chunk: {stats.max_embed_tokens} tokens (budget {stats.chunk_budget})")


def _query(args: argparse.Namespace) -> None:
    embedder = get_embedder(settings)
    index = VectorIndex(settings.chroma_persist_dir, embedder)
    where = build_filter(doc_type=args.type, service=args.service, tier=args.tier)
    for rank, hit in enumerate(index.query(args.text, k=args.k, where=where), start=1):
        meta = hit.metadata
        section = f" [{meta['section']}]" if "section" in meta else ""
        print(f"{rank}. {hit.score:.3f}  {meta['doc_type']}  tier={meta['tier']}  {hit.chunk_id}{section}")
        print(f"     {hit.text[:110].replace(chr(10), ' ')}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m meridian.indexing")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="chunk, embed, and (re)build the index")
    query = sub.add_parser("query", help="similarity search over the index")
    query.add_argument("text")
    query.add_argument("-k", type=int, default=5)
    query.add_argument("--type", dest="type")
    query.add_argument("--service")
    query.add_argument("--tier")
    args = parser.parse_args(argv)

    if args.command == "build":
        _build()
    else:
        _query(args)


if __name__ == "__main__":
    main()
