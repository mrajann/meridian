"""Chunking strategy tests.

Uses a plain word counter as the token counter so budgets are exact. The real
corpus never needs splitting for size (its longest document is 153 tokens
against a 256-token model limit), so the oversize paths -- the ones that
matter for real-length documents -- are exercised here on synthetic
documents instead of being dead code on this corpus.
"""

import re

from meridian.corpus.models import CorpusDocument
from meridian.indexing.chunking import chunk_document


def count(text: str) -> int:
    return len(text.split())


def make_doc(doc_type: str, body: str, title: str = "rb one", services=("svc",)) -> CorpusDocument:
    return CorpusDocument(
        doc_id=f"{doc_type}-x", doc_type=doc_type, title=title, services=list(services), body=body
    )


def words(prefix: str, n: int) -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


def assert_within_budget(chunks, max_tokens):
    for chunk in chunks:
        assert count(chunk.embed_text) <= max_tokens, f"{chunk.chunk_id} is {count(chunk.embed_text)} tokens"


# ------------------------------------------------------------------ headers


def test_short_runbook_is_one_chunk_with_a_context_header():
    doc = make_doc("runbook", "Symptom.\n\nRoot cause.\n\nFix.", title="checkout-api: 5xx", services=("checkout-api", "postgres-primary"))

    chunks = chunk_document(doc, count, 100)

    assert len(chunks) == 1
    assert chunks[0].text == doc.body
    assert chunks[0].header.startswith("Runbook: checkout-api: 5xx")
    assert "Services: checkout-api, postgres-primary" in chunks[0].header
    assert chunks[0].embed_text.startswith(chunks[0].header)


def test_header_does_not_repeat_a_type_label_the_title_already_has():
    doc = make_doc("postmortem", "Summary: a.", title="Postmortem: llm-gateway rate limit")

    header = chunk_document(doc, count, 100)[0].header

    assert header.startswith("Postmortem: llm-gateway rate limit")
    assert "Postmortem: Postmortem" not in header


def test_header_caps_long_service_lists():
    doc = make_doc("alert", "Something broke.", services=("a", "b", "c", "d", "e", "f"))

    header = chunk_document(doc, count, 100)[0].header

    assert "Services: a, b, c (+3 more)" in header


def test_empty_body_yields_no_chunks():
    assert chunk_document(make_doc("runbook", "   \n\n  "), count, 100) == []


# ---------------------------------------------------------------- runbooks


def test_procedure_stays_in_one_chunk_when_it_fits():
    steps = "Follow these steps:\n" + "\n".join(f"{i}. {words('s', 6)}" for i in range(1, 6))
    body = f"{words('a', 30)}\n\n{steps}\n\n{words('c', 30)}"
    doc = make_doc("runbook", body)

    chunks = chunk_document(doc, count, 60)

    assert len(chunks) == 3, "filler, procedure, filler don't fit together, so each block lands alone"
    step_counts = [sum(1 for line in c.text.split("\n") if line[:2] in {f"{i}." for i in range(1, 6)}) for c in chunks]
    assert sorted(step_counts) == [0, 0, 5], "all five steps must be in one chunk, never split"
    assert_within_budget(chunks, 60)


def test_procedure_longer_than_the_budget_splits_only_between_steps():
    lead_in = "Follow these steps:"
    # Uneven step lengths so a size-based cut can't land on a step boundary by luck.
    step_lines = [f"{i}. {words('w', 5 + (i * 3) % 7)}" for i in range(1, 9)]
    doc = make_doc("runbook", lead_in + "\n" + "\n".join(step_lines))

    chunks = chunk_document(doc, count, 40)

    assert len(chunks) >= 2
    for chunk in chunks:
        for line in chunk.text.split("\n"):
            assert line == lead_in or re.match(r"\d+\. ", line), f"chunk starts or ends mid-step: {line!r}"
    all_lines = [line for c in chunks for line in c.text.split("\n")]
    for step in step_lines:
        assert all_lines.count(step) == 1, f"step split or duplicated: {step!r}"
    first_chunk_lines = chunks[0].text.split("\n")
    assert first_chunk_lines[0] == lead_in and first_chunk_lines[1] == step_lines[0]
    assert_within_budget(chunks, 60)


def test_oversize_paragraph_falls_back_to_sentence_windows_with_one_sentence_overlap():
    sentences = [f"S{i} one two three four five six seven eight nine." for i in range(9)]
    doc = make_doc("runbook", " ".join(sentences))

    chunks = chunk_document(doc, count, 40)

    assert len(chunks) > 1
    for previous, following in zip(chunks, chunks[1:]):
        prev_sentences = previous.text.split(". ")
        assert following.text.startswith(prev_sentences[-1].rstrip(".")), "windows should overlap by one sentence"
    covered = " ".join(c.text for c in chunks)
    for sentence in sentences:
        assert sentence.rstrip(".") in covered
    assert_within_budget(chunks, 40)


# -------------------------------------------------------------- postmortems


POSTMORTEM = (
    "Summary: the disk filled up and writes were refused.\n\n"
    "Root cause: unshipped WAL segments accumulated.\n\n"
    "Action items: alert on disk usage at eighty percent."
)


def test_postmortem_is_one_chunk_per_section_with_no_overlap():
    doc = make_doc("postmortem", POSTMORTEM, title="Postmortem: pg disk")

    chunks = chunk_document(doc, count, 100)

    assert [c.section for c in chunks] == ["Summary", "Root cause", "Action items"]
    assert [c.text.split(":")[0] for c in chunks] == ["Summary", "Root cause", "Action items"]
    assert "\n\n".join(c.text for c in chunks) == POSTMORTEM, "sections are a lossless, non-overlapping partition"
    assert "— Root cause" in chunks[1].header


def test_small_postmortem_sections_are_not_merged():
    assert len(chunk_document(make_doc("postmortem", POSTMORTEM), count, 500)) == 3


def test_postmortem_recognizes_timeline_and_remediation_headings():
    body = "Summary: s.\n\nTimeline: 10:00 alert. 10:05 page.\n\nRoot cause: r.\n\nRemediation: rolled back."

    sections = [c.section for c in chunk_document(make_doc("postmortem", body), count, 100)]

    assert sections == ["Summary", "Timeline", "Root cause", "Remediation"]


def test_heading_match_is_case_insensitive_and_canonicalized():
    chunks = chunk_document(make_doc("postmortem", "ROOT CAUSE: r.\n\naction ITEMS: a."), count, 100)

    assert [c.section for c in chunks] == ["Root cause", "Action items"]


def test_postmortem_without_headings_is_a_single_body_chunk():
    chunks = chunk_document(make_doc("postmortem", "Just some prose about an outage."), count, 100)

    assert [c.section for c in chunks] == ["Body"]


def test_text_before_the_first_heading_becomes_a_preamble_section():
    chunks = chunk_document(make_doc("postmortem", "Incident 42.\n\nSummary: s.\n\nRoot cause: r."), count, 100)

    assert [c.section for c in chunks] == ["Preamble", "Summary", "Root cause"]


def test_oversize_postmortem_section_splits_within_the_section():
    body = f"Summary: short.\n\nRoot cause: {words('a', 30)}\n\n{words('b', 30)}"

    chunks = chunk_document(make_doc("postmortem", body, title="Postmortem: pm"), count, 60)

    root_cause = [c for c in chunks if c.section == "Root cause"]
    assert len(root_cause) == 2
    assert all(c.section in {"Summary", "Root cause"} for c in chunks)
    assert_within_budget(chunks, 60)


# -------------------------------------------------------------------- chat


def turn(i: int) -> str:
    return f"[+{i}m] @dev: {words('t', 5)}"


def test_short_chat_transcript_is_one_chunk():
    doc = make_doc("chat_transcript", "\n".join(turn(i) for i in range(5)))

    chunks = chunk_document(doc, count, 100)

    assert len(chunks) == 1
    assert chunks[0].text.count("\n") == 4


def test_chat_windows_overlap_by_exactly_two_turns_and_cover_everything():
    turns = [turn(i) for i in range(30)]
    doc = make_doc("chat_transcript", "\n".join(turns))

    chunks = chunk_document(doc, count, 60)

    windows = [c.text.split("\n") for c in chunks]
    assert len(windows) > 2
    for previous, following in zip(windows, windows[1:]):
        assert previous[-2:] == following[:2], "consecutive windows must share their boundary turns"
    seen = []
    for window in windows:
        assert all(t in turns for t in window), "a turn must never be cut mid-line"
        seen.extend(t for t in window if t not in seen)
    assert seen == turns
    assert_within_budget(chunks, 60)


def test_chat_makes_progress_when_turns_are_large_relative_to_the_budget():
    big = [f"[+{i}m] @dev: {words('t', 20)}" for i in range(8)]
    doc = make_doc("chat_transcript", "\n".join(big))

    chunks = chunk_document(doc, count, 60)

    windows = [tuple(c.text.split("\n")) for c in chunks]
    assert len(set(windows)) == len(windows), "no window may repeat the previous window's tail"
    assert set(t for w in windows for t in w) == set(big)


def test_a_single_oversize_chat_turn_is_split_by_sentence():
    long_turn = "[+0m] @dev: " + " ".join(f"S{i} one two three four five six seven eight nine." for i in range(10))
    doc = make_doc("chat_transcript", long_turn + "\n[+1m] @sam: ok")

    chunks = chunk_document(doc, count, 50)

    assert len(chunks) > 2
    assert_within_budget(chunks, 50)


# ---------------------------------------------------------- atomic + shape


def test_alerts_and_catalog_entries_are_single_chunks():
    assert len(chunk_document(make_doc("alert", "svc: 5xx spike. Investigate."), count, 100)) == 1
    catalog = make_doc("catalog_entry", "Desc.\n\nOwner: team. Tier: 1.\nDepends on: a.", title="Service catalog: svc")
    assert len(chunk_document(catalog, count, 100)) == 1


def test_chunk_ids_are_stable_and_ordered():
    doc = make_doc("postmortem", POSTMORTEM)

    first = [c.chunk_id for c in chunk_document(doc, count, 100)]
    second = [c.chunk_id for c in chunk_document(doc, count, 100)]

    assert first == second == ["postmortem-x::00", "postmortem-x::01", "postmortem-x::02"]


def test_no_content_is_lost_across_every_strategy():
    docs = [
        make_doc("runbook", f"{words('a', 40)}\n\n1. {words('s', 9)}\n2. {words('t', 9)}\n\n{words('c', 40)}"),
        make_doc("postmortem", f"Summary: {words('a', 30)}\n\nRoot cause: {words('b', 45)}"),
        make_doc("chat_transcript", "\n".join(turn(i) for i in range(20))),
        make_doc("alert", words("x", 20)),
    ]
    for doc in docs:
        covered = " ".join(c.text for c in chunk_document(doc, count, 60)).split()
        assert set(doc.body.split()) <= set(covered), f"{doc.doc_type} lost content"
