"""Corpus document schema and markdown+frontmatter (de)serialization."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

CORPUS_DIR = Path(__file__).resolve().parents[3] / "data" / "corpus"

DocType = Literal["runbook", "postmortem", "alert", "chat_transcript", "catalog_entry"]

# Subdirectory under CORPUS_DIR that each doc type is written to / read from.
_SUBDIR = {
    "runbook": "runbooks",
    "postmortem": "postmortems",
    "alert": "alerts",
    "chat_transcript": "chat_transcripts",
    "catalog_entry": "catalog_entries",
}


class CorpusDocument(BaseModel):
    """One retrievable document. `metadata` carries doc-type-specific fields
    (root_cause_category, correct_runbook, affected_services, ...) rather than
    a rigid per-type schema -- the five document types share little structure
    beyond "some text about some services", and a discriminated union of five
    near-empty classes would add ceremony without adding safety here.
    """

    doc_id: str
    doc_type: DocType
    title: str
    services: list[str] = Field(default_factory=list)
    body: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_markdown(self) -> str:
        frontmatter = {
            "doc_id": self.doc_id,
            "doc_type": self.doc_type,
            "title": self.title,
            "services": self.services,
            "metadata": self.metadata,
        }
        header = yaml.safe_dump(frontmatter, sort_keys=False)
        return f"---\n{header}---\n\n{self.body.strip()}\n"

    @classmethod
    def from_markdown(cls, text: str) -> CorpusDocument:
        _, frontmatter_text, body = text.split("---", 2)
        frontmatter = yaml.safe_load(frontmatter_text)
        return cls(**frontmatter, body=body.strip())


def write_corpus(documents: list[CorpusDocument], directory: Path = CORPUS_DIR) -> None:
    for doc_type, subdir in _SUBDIR.items():
        (directory / subdir).mkdir(parents=True, exist_ok=True)

    for doc in documents:
        path = directory / _SUBDIR[doc.doc_type] / f"{doc.doc_id}.md"
        path.write_text(doc.to_markdown())


def load_corpus(directory: Path = CORPUS_DIR) -> list[CorpusDocument]:
    documents = []
    for subdir in _SUBDIR.values():
        for path in sorted((directory / subdir).glob("*.md")):
            documents.append(CorpusDocument.from_markdown(path.read_text()))
    return documents
