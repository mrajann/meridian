"""Synthetic incident corpus: documents, generation, and disk I/O."""

from meridian.catalog import ServiceEntry
from meridian.corpus import generator as _generator
from meridian.corpus import scale as _scale
from meridian.corpus.generator import (
    DECOMMISSIONED_SERVICES,
    FRAGILE_SERVICES,
    generate_alerts,
    generate_catalog_documents,
    generate_chat_transcripts,
    generate_postmortems,
    generate_runbooks,
)
from meridian.corpus.models import CORPUS_DIR, CorpusDocument, load_corpus, write_corpus
from meridian.corpus.scale import (
    generate_alerts_v2,
    generate_catalog_documents_v2,
    generate_chat_transcripts_v2,
    generate_postmortems_v2,
    generate_runbooks_v2,
)


def generate_corpus(catalog: dict[str, ServiceEntry]) -> list[CorpusDocument]:
    """The full corpus: the original 32 hand-authored documents (increment 3)
    plus the ~250-document template-generated expansion, combined."""
    batch1 = _generator.generate_corpus(catalog)
    batch1_runbooks = [d for d in batch1 if d.doc_type == "runbook"]
    batch2 = _scale.generate_corpus_v2(catalog, batch1_runbooks)
    return [*batch1, *batch2]


__all__ = [
    "CORPUS_DIR",
    "CorpusDocument",
    "DECOMMISSIONED_SERVICES",
    "FRAGILE_SERVICES",
    "generate_alerts",
    "generate_alerts_v2",
    "generate_catalog_documents",
    "generate_catalog_documents_v2",
    "generate_chat_transcripts",
    "generate_chat_transcripts_v2",
    "generate_corpus",
    "generate_postmortems",
    "generate_postmortems_v2",
    "generate_runbooks",
    "generate_runbooks_v2",
    "load_corpus",
    "write_corpus",
]
