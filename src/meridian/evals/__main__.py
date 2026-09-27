"""Run retrieval evals and write the report.

    python -m meridian.evals retrieval
    python -m meridian.evals retrieval --out reports/retrieval_eval.md --k 5
"""

from __future__ import annotations

import argparse
from pathlib import Path

from meridian.config import settings
from meridian.corpus import load_corpus
from meridian.evals.report import render_markdown
from meridian.evals.retrieval import DEFAULT_K, evaluate_retrieval
from meridian.indexing.embeddings import get_embedder
from meridian.indexing.store import VectorIndex
from meridian.retrieval import Retriever

DEFAULT_REPORT_PATH = Path("reports/retrieval_eval.md")


def _retrieval(args: argparse.Namespace) -> None:
    embedder = get_embedder(settings)
    retriever = Retriever(VectorIndex(settings.chroma_persist_dir, embedder))
    # load_corpus(), not generate_corpus(): must read the same documents the
    # index was actually built from (meridian.indexing build also reads from
    # disk), or a corpus-generation change that hasn't been re-written to
    # disk yet silently evaluates against different text than what's indexed.
    documents = load_corpus()

    report = evaluate_retrieval(retriever, documents, embedder_name=embedder.name, k=args.k)
    markdown = render_markdown(report)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(markdown)
    print(markdown)
    print(f"\nwrote {args.out}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m meridian.evals")
    sub = parser.add_subparsers(dest="command", required=True)

    retrieval = sub.add_parser("retrieval", help="Hit@1/recall@k/MRR + no-match and stale-contamination analysis")
    retrieval.add_argument("--out", type=Path, default=DEFAULT_REPORT_PATH)
    retrieval.add_argument("--k", type=int, default=DEFAULT_K)

    args = parser.parse_args(argv)
    if args.command == "retrieval":
        _retrieval(args)


if __name__ == "__main__":
    main()
