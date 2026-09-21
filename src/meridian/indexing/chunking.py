"""Type-aware chunking.

One fixed chunk size would be wrong for most of this corpus, so the split
strategy depends on the document type:

- runbook, alert, catalog entry: whole paragraphs are packed greedily into
  chunks up to the token budget. Anything that fits is a single chunk, and
  a numbered/bulleted procedure is never cut between a lead-in and its
  steps or in the middle of a step (only a list longer than the whole budget
  is split, and then only between steps).
- postmortem: one chunk per named section (Summary, Timeline, Root cause,
  Remediation, ...). Small sections are deliberately NOT merged -- being
  separately retrievable is the point. An over-budget section is split by
  paragraph, keeping its section label.
- chat transcript: sliding window of whole turns (never mid-line) with a
  two-turn overlap, since a question and its answer straddling a cut is the
  main way a conversation loses meaning.

Overlap is used only where a boundary is arbitrary (chat windows, a lone
oversize paragraph split by sentences). Section/step/paragraph boundaries are
already semantic seams, so overlapping there would only duplicate text and put
near-identical hits in top-k. Context is carried instead by a header (type,
title, services) that is embedded with each chunk but not stored as content.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from meridian.corpus.models import CorpusDocument

TokenCounter = Callable[[str], int]

CHAT_OVERLAP_TURNS = 2
SENTENCE_OVERLAP = 1
MAX_HEADER_SERVICES = 3
MIN_BODY_BUDGET = 32

POSTMORTEM_SECTIONS = (
    "Summary",
    "Timeline",
    "Impact",
    "Detection",
    "Root cause",
    "Contributing factors",
    "Remediation",
    "Resolution",
    "Action items",
    "Lessons learned",
)
_CANONICAL_SECTION = {s.lower(): s for s in POSTMORTEM_SECTIONS}
_SECTION_RE = re.compile(
    r"^(" + "|".join(re.escape(s) for s in POSTMORTEM_SECTIONS) + r")\s*:", re.IGNORECASE | re.MULTILINE
)
_STEP_RE = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

_TYPE_LABEL = {
    "runbook": "Runbook",
    "postmortem": "Postmortem",
    "alert": "Alert",
    "chat_transcript": "Chat transcript",
    "catalog_entry": "Service catalog",
}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    doc_type: str
    index: int
    title: str
    services: tuple[str, ...]
    section: str | None
    header: str
    text: str

    @property
    def embed_text(self) -> str:
        return f"{self.header}\n{self.text}"


def _header(doc: CorpusDocument, section: str | None = None) -> str:
    label = _TYPE_LABEL[doc.doc_type]
    lead = doc.title if doc.title.lower().startswith(label.lower()) else f"{label}: {doc.title}"
    if section:
        lead += f" — {section}"
    if not doc.services:
        return lead
    shown = ", ".join(doc.services[:MAX_HEADER_SERVICES])
    extra = len(doc.services) - MAX_HEADER_SERVICES
    if extra > 0:
        shown += f" (+{extra} more)"
    return f"{lead}\nServices: {shown}"


# ---------------------------------------------------------------- splitting


def _sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE_SPLIT.split(text.strip()) if s]


def _hard_split_words(text: str, budget: int, count: TokenCounter) -> list[str]:
    """Last resort for a single sentence longer than the whole budget."""
    pieces: list[str] = []
    current: list[str] = []
    for word in text.split():
        if current and count(" ".join([*current, word])) > budget:
            pieces.append(" ".join(current))
            current = []
        current.append(word)
    if current:
        pieces.append(" ".join(current))
    return pieces


def _next_start(items: list[str], i: int, j: int, max_overlap: int, sep: str, budget: int, count: TokenCounter) -> int:
    """Where the next window starts after items[i:j]: back up by as much of
    `max_overlap` as still leaves room for at least one new item, so a window
    is never just a repeat of the previous one's tail."""
    for overlap in range(max_overlap, -1, -1):
        start = j - overlap
        if start <= i:
            continue
        if count(sep.join(items[start : j + 1])) <= budget:
            return start
    return j


def _windows(
    items: list[str],
    sep: str,
    budget: int,
    count: TokenCounter,
    max_overlap: int,
    split_item: Callable[[str], list[str]],
) -> list[str]:
    out: list[str] = []
    n = len(items)
    i = 0
    while i < n:
        if count(items[i]) > budget:
            out.extend(split_item(items[i]))
            i += 1
            continue
        j = i + 1
        while j < n and count(sep.join(items[i : j + 1])) <= budget:
            j += 1
        out.append(sep.join(items[i:j]))
        if j >= n:
            break
        i = _next_start(items, i, j, max_overlap, sep, budget, count)
    return out


def _split_sentences(text: str, budget: int, count: TokenCounter) -> list[str]:
    return _windows(
        _sentences(text), " ", budget, count, SENTENCE_OVERLAP, lambda s: _hard_split_words(s, budget, count)
    )


def _pack(blocks: list[str], sep: str, budget: int, count: TokenCounter, split_oversize) -> list[str]:
    """Greedy, no-overlap packing of atomic blocks. A block is only ever cut
    if it alone exceeds the budget."""
    chunks: list[str] = []
    current: list[str] = []
    for block in blocks:
        pieces = [block] if count(block) <= budget else split_oversize(block)
        for piece in pieces:
            if current and count(sep.join([*current, piece])) > budget:
                chunks.append(sep.join(current))
                current = []
            current.append(piece)
    if current:
        chunks.append(sep.join(current))
    return chunks


def _split_steps(lines: list[str], budget: int, count: TokenCounter) -> list[str]:
    steps: list[str] = []
    for line in lines:
        if _STEP_RE.match(line) or not steps:
            steps.append(line)
        else:
            steps[-1] += "\n" + line
    # A lead-in line ("Follow these steps:") stays attached to the first step.
    if len(steps) > 1 and not _STEP_RE.match(steps[0].split("\n")[0]):
        steps[1] = steps[0] + "\n" + steps[1]
        steps = steps[1:]
    return _pack(steps, "\n", budget, count, lambda step: _split_sentences(step, budget, count))


def _split_block(block: str, budget: int, count: TokenCounter) -> list[str]:
    lines = block.split("\n")
    if any(_STEP_RE.match(line) for line in lines):
        return _split_steps(lines, budget, count)
    return _split_sentences(block, budget, count)


def _paragraphs(text: str, budget: int, count: TokenCounter) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    return _pack(blocks, "\n\n", budget, count, lambda block: _split_block(block, budget, count))


# --------------------------------------------------------------- strategies

Piece = tuple[str | None, str, str]  # (section, header, text)


def _prose(doc: CorpusDocument, count: TokenCounter, max_tokens: int) -> list[Piece]:
    header = _header(doc)
    budget = max(max_tokens - count(header), MIN_BODY_BUDGET)
    return [(None, header, text) for text in _paragraphs(doc.body, budget, count)]


def _postmortem_sections(body: str) -> list[tuple[str, str]]:
    matches = list(_SECTION_RE.finditer(body))
    if not matches:
        return [("Body", body.strip())]
    sections: list[tuple[str, str]] = []
    preamble = body[: matches[0].start()].strip()
    if preamble:
        sections.append(("Preamble", preamble))
    for k, match in enumerate(matches):
        end = matches[k + 1].start() if k + 1 < len(matches) else len(body)
        sections.append((_CANONICAL_SECTION[match.group(1).lower()], body[match.start() : end].strip()))
    return sections


def _postmortem(doc: CorpusDocument, count: TokenCounter, max_tokens: int) -> list[Piece]:
    pieces: list[Piece] = []
    for section, text in _postmortem_sections(doc.body):
        header = _header(doc, section)
        budget = max(max_tokens - count(header), MIN_BODY_BUDGET)
        pieces.extend((section, header, part) for part in _paragraphs(text, budget, count))
    return pieces


def _chat(doc: CorpusDocument, count: TokenCounter, max_tokens: int) -> list[Piece]:
    header = _header(doc)
    budget = max(max_tokens - count(header), MIN_BODY_BUDGET)
    turns = [line.strip() for line in doc.body.splitlines() if line.strip()]
    windows = _windows(
        turns, "\n", budget, count, CHAT_OVERLAP_TURNS, lambda turn: _split_sentences(turn, budget, count)
    )
    return [(None, header, text) for text in windows]


_STRATEGIES: dict[str, Callable[[CorpusDocument, TokenCounter, int], list[Piece]]] = {
    "runbook": _prose,
    "alert": _prose,
    "catalog_entry": _prose,
    "postmortem": _postmortem,
    "chat_transcript": _chat,
}


def chunk_document(doc: CorpusDocument, count_tokens: TokenCounter, max_tokens: int) -> list[Chunk]:
    """Split one document. `max_tokens` bounds header + text together."""
    pieces = _STRATEGIES[doc.doc_type](doc, count_tokens, max_tokens)
    return [
        Chunk(
            chunk_id=f"{doc.doc_id}::{i:02d}",
            doc_id=doc.doc_id,
            doc_type=doc.doc_type,
            index=i,
            title=doc.title,
            services=tuple(doc.services),
            section=section,
            header=header,
            text=text,
        )
        for i, (section, header, text) in enumerate(pieces)
    ]


def chunk_corpus(documents: list[CorpusDocument], count_tokens: TokenCounter, max_tokens: int) -> list[Chunk]:
    return [chunk for doc in documents for chunk in chunk_document(doc, count_tokens, max_tokens)]
