"""Synthetic incident corpus: documents, generation, and disk I/O."""

from meridian.corpus.generator import (
    DECOMMISSIONED_SERVICES,
    FRAGILE_SERVICES,
    generate_alerts,
    generate_catalog_documents,
    generate_chat_transcripts,
    generate_corpus,
    generate_postmortems,
    generate_runbooks,
)
from meridian.corpus.models import CORPUS_DIR, CorpusDocument, load_corpus, write_corpus

__all__ = [
    "CORPUS_DIR",
    "CorpusDocument",
    "DECOMMISSIONED_SERVICES",
    "FRAGILE_SERVICES",
    "generate_alerts",
    "generate_catalog_documents",
    "generate_chat_transcripts",
    "generate_corpus",
    "generate_postmortems",
    "generate_runbooks",
    "load_corpus",
    "write_corpus",
]
