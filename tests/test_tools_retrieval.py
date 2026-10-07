import json
from types import SimpleNamespace

import pytest

from meridian.indexing.store import Hit, build_filter
from meridian.tools import Toolset, ToolError
from meridian.tools.retrieval_tools import SCORE_GUIDE, _search

ROW_KEYS = {"rank", "doc_id", "doc_type", "title", "services", "cosine_similarity", "fused_score", "text"}
GROUND_TRUTH_KEYS = {
    "correct_runbook", "has_matching_runbook", "root_cause_service", "root_cause_category",
    "adversarial_case", "fragile_service", "stale_reference", "affected_services",
}


def call(ctx, name, /, **kwargs):
    return Toolset(ctx).functions[name](**kwargs)


def chunk(doc_id, n=0, score=0.5, doc_type="runbook", section=None):
    metadata = {"doc_id": doc_id, "doc_type": doc_type, "title": f"title {doc_id}", "services": ["svc"]}
    if section:
        metadata["section"] = section
    return Hit(chunk_id=f"{doc_id}::{n:02d}", text=f"text {doc_id} {n}", score=score, metadata=metadata)


class StubRetriever:
    """Returns canned hits per mode and records cosine look-ups."""

    def __init__(self, fused, vector, extra_cosines=None):
        self._by_mode = {"hybrid": fused, "vector": vector}
        self.cosine_requests = []
        self.vector_index = SimpleNamespace(cosine_similarities=self._cosines)
        self._extra = extra_cosines or {}

    def search(self, query, k=5, where=None, mode="vector"):
        return self._by_mode[mode][:k]

    def _cosines(self, query, chunk_ids):
        self.cosine_requests.append(list(chunk_ids))
        return {cid: self._extra[cid] for cid in chunk_ids}


def stub_ctx(retriever, excluded=()):
    return SimpleNamespace(retriever=retriever, excluded_doc_ids=frozenset(excluded))


# ----------------------------------------------------------- _search: edge cases


def test_no_results_gives_empty_results_and_null_signals():
    ctx = stub_ctx(StubRetriever(fused=[], vector=[]))

    result = _search(ctx, "q", 5, "runbook")

    assert result["results"] == [] and result["top1_cosine_similarity"] is None and result["gap_to_second_hit"] is None


def test_a_single_document_has_a_top1_but_no_gap():
    hit = chunk("a", score=0.7)
    result = _search(stub_ctx(StubRetriever([hit], [hit])), "q", 5, "runbook")

    assert result["top1_cosine_similarity"] == 0.7 and result["gap_to_second_hit"] is None


def test_the_gap_is_between_distinct_documents_not_chunks_of_the_same_one():
    vector = [chunk("a", 0, 0.9), chunk("a", 1, 0.85), chunk("b", 0, 0.5)]
    result = _search(stub_ctx(StubRetriever([chunk("a", 0, 3.0)], vector)), "q", 5, "postmortem")

    assert result["top1_cosine_similarity"] == 0.9 and result["gap_to_second_hit"] == 0.4


def test_a_document_appears_once_keeping_its_best_fused_chunk():
    fused = [chunk("a", 1, 3.5), chunk("a", 0, 3.0), chunk("b", 0, 2.0)]
    result = _search(stub_ctx(StubRetriever(fused, [chunk("a", 1, 0.8), chunk("b", 0, 0.5)])), "q", 5, "postmortem")

    assert [(r["doc_id"], r["rank"]) for r in result["results"]] == [("a", 1), ("b", 2)]
    assert "a 1" in result["results"][0]["text"]  # the chunk that ranked highest, not the first by index


def test_excluded_documents_vanish_from_results_and_from_the_cosine_signals():
    vector = [chunk("self", 0, 0.95), chunk("b", 0, 0.6), chunk("c", 0, 0.5)]
    fused = [chunk("self", 0, 3.9), chunk("b", 0, 3.0), chunk("c", 0, 2.0)]
    result = _search(stub_ctx(StubRetriever(fused, vector), excluded={"self"}), "q", 5, "runbook")

    assert [r["doc_id"] for r in result["results"]] == ["b", "c"]
    assert result["top1_cosine_similarity"] == 0.6 and result["gap_to_second_hit"] == pytest.approx(0.1)


def test_k_applies_after_deduplication_and_exclusion():
    fused = [chunk("x", 0, 3.0), chunk("a", 0, 2.9), chunk("a", 1, 2.8), chunk("b", 0, 2.7), chunk("c", 0, 2.6)]
    vector = [chunk(d, 0, 0.5) for d in "abc"]
    result = _search(stub_ctx(StubRetriever(fused, vector), excluded={"x"}), "q", 2, "runbook")

    assert [r["doc_id"] for r in result["results"]] == ["a", "b"]


def test_a_hit_found_only_by_keyword_search_gets_its_cosine_looked_up_and_only_it():
    fused = [chunk("a", 0, 3.5), chunk("kw", 0, 1.0)]
    retriever = StubRetriever(fused, [chunk("a", 0, 0.8)], extra_cosines={"kw::00": 0.4321987})

    result = _search(stub_ctx(retriever), "q", 5, "runbook")

    assert retriever.cosine_requests == [["kw::00"]]
    assert [r["cosine_similarity"] for r in result["results"]] == [0.8, 0.4322]


def test_no_lookup_is_made_when_every_hit_already_has_a_vector_score():
    retriever = StubRetriever([chunk("a", 0, 3.0)], [chunk("a", 0, 0.8)])

    _search(stub_ctx(retriever), "q", 5, "runbook")

    assert retriever.cosine_requests == [[]]


def test_scores_are_rounded_to_four_places():
    hit = chunk("a", 0, 0.123456789)
    result = _search(stub_ctx(StubRetriever([chunk("a", 0, 3.123456789)], [hit])), "q", 5, "runbook")

    assert result["results"][0]["cosine_similarity"] == 0.1235 and result["results"][0]["fused_score"] == 3.1235


# ------------------------------------------------- the two scores, on the real index


@pytest.fixture
def reference(s_retriever):
    """reference(query, doc_type) -> {chunk_id: cosine} over *every* chunk of that type."""
    index = s_retriever.vector_index

    def build(query, doc_type):
        where = build_filter(doc_type=doc_type)
        return {h.chunk_id: h.score for h in index.query(query, k=index.count(), where=where)}

    return build


@pytest.mark.parametrize(
    "tool, arg, doc_type",
    [
        ("search_runbooks", "query", "runbook"),
        ("search_postmortems", "query", "postmortem"),
        ("find_similar_incidents", "description", ["alert", "postmortem"]),
    ],
)
def test_every_reported_cosine_equals_the_true_vector_cosine_of_that_chunk(s_ctx, reference, tool, arg, doc_type):
    checked = 0
    for query in ("database connections maxed out", "error rate elevated after deploy", "sms messages not delivered"):
        truth = reference(query, doc_type)
        result = call(s_ctx, tool, **{arg: query, "k": 10})
        by_chunk = {r["doc_id"]: r for r in result["results"]}
        for hit in s_ctx.retriever.vector_index.query(query, k=len(truth), where=build_filter(doc_type=doc_type)):
            if hit.doc_id in by_chunk and hit.text == by_chunk[hit.doc_id]["text"]:
                assert by_chunk[hit.doc_id]["cosine_similarity"] == pytest.approx(truth[hit.chunk_id], abs=1e-4)
                checked += 1
    assert checked >= 15, "too few rows compared for this to mean anything"


def test_keyword_only_hits_really_occur_and_their_cosines_are_still_correct(s_ctx, s_documents, reference, monkeypatch):
    index = s_ctx.retriever.vector_index
    looked_up = []
    original = index.cosine_similarities

    def spy(text, chunk_ids):
        looked_up.extend(chunk_ids)
        return original(text, chunk_ids)

    monkeypatch.setattr(index, "cosine_similarities", spy)

    checked = 0
    for alert in (d for d in s_documents if d.doc_type == "alert"):
        truth = reference(alert.body, "runbook")
        before = len(looked_up)
        result = call(s_ctx, "search_runbooks", query=alert.body[:500], k=10)
        if len(looked_up) > before:
            fetched = set(looked_up[before:])
            for row in result["results"]:
                chunk_id = f"{row['doc_id']}::00"
                if chunk_id in fetched:
                    assert row["cosine_similarity"] == pytest.approx(truth[chunk_id], abs=1e-4)
                    checked += 1

    assert checked > 0, "the keyword-only path was never exercised: this test would prove nothing"


def test_top1_and_gap_are_the_best_two_documents_by_vector_ranking(s_ctx, reference):
    query = "database connections maxed out"
    per_doc = {}
    for chunk_id, score in reference(query, "runbook").items():
        doc_id = chunk_id.split("::")[0]
        per_doc[doc_id] = max(per_doc.get(doc_id, -1), score)
    ranked = sorted(per_doc.values(), reverse=True)

    result = call(s_ctx, "search_runbooks", query=query)

    assert result["top1_cosine_similarity"] == pytest.approx(ranked[0], abs=1e-4)
    assert result["gap_to_second_hit"] == pytest.approx(ranked[0] - ranked[1], abs=1e-4)


def test_results_are_ordered_by_the_fused_score(s_ctx):
    rows = call(s_ctx, "search_runbooks", query="checkout-api latency above target", k=10)["results"]

    scores = [r["fused_score"] for r in rows]
    assert scores == sorted(scores, reverse=True) and [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    assert all(0.0 <= s <= 4.0 for s in scores)


def test_the_fused_ranking_and_the_cosine_can_disagree_which_is_why_both_are_returned(s_ctx, s_documents):
    disagreements = 0
    for alert in (d for d in s_documents if d.doc_type == "alert"):
        rows = call(s_ctx, "search_runbooks", query=alert.body[:500], k=5)["results"]
        cosines = [r["cosine_similarity"] for r in rows]
        disagreements += cosines != sorted(cosines, reverse=True)

    assert disagreements > 0


def test_the_score_guide_labels_both_scores_and_warns_the_fused_one_is_not_comparable(s_ctx):
    result = call(s_ctx, "search_runbooks", query="connection pool exhausted")

    guide = result["score_guide"]
    assert guide == SCORE_GUIDE and {"cosine_similarity", "fused_score", "top1_cosine_similarity", "gap_to_second_hit"} <= set(guide)
    assert "Absolute scale" in guide["cosine_similarity"]
    assert "normalized per query" in guide["fused_score"] and "not comparable" in guide["fused_score"]


# ----------------------------------------------------------------- per-tool behavior


def test_search_runbooks_returns_only_runbooks(s_ctx):
    result = call(s_ctx, "search_runbooks", query="elevated 5xx error rate", k=10)

    assert result["results"] and {r["doc_type"] for r in result["results"]} == {"runbook"}
    assert result["query"] == "elevated 5xx error rate"
    json.dumps(result)


def test_search_runbooks_finds_a_runbook_that_uses_the_queried_wording(s_ctx):
    rows = call(s_ctx, "search_runbooks", query="database connections maxed out", k=5)["results"]

    assert any("maxed out" in r["text"] for r in rows)


def test_search_postmortems_returns_one_section_per_postmortem(s_ctx):
    rows = call(s_ctx, "search_postmortems", query="writes refused and many services erroring at once", k=10)["results"]

    assert rows and {r["doc_type"] for r in rows} == {"postmortem"}
    assert len({r["doc_id"] for r in rows}) == len(rows)
    assert all(r["section"] in {"Summary", "Root cause", "Action items"} for r in rows)


def test_find_similar_incidents_searches_both_alerts_and_postmortems(s_ctx):
    rows = call(s_ctx, "find_similar_incidents", description="5xx spike across several services at once", k=10)["results"]

    assert {r["doc_type"] for r in rows} == {"alert", "postmortem"}


def test_k_limits_the_number_of_results(s_ctx):
    assert len(call(s_ctx, "search_runbooks", query="latency", k=3)["results"]) == 3
    assert len(call(s_ctx, "search_runbooks", query="latency", k=1)["results"]) == 1


# ------------------------------------------------------------- no answer leakage


def test_the_investigated_incident_cannot_find_itself(s_documents, s_ctx, ctx_for):
    alert = next(d for d in s_documents if d.doc_type == "alert")

    without = call(s_ctx, "find_similar_incidents", description=alert.body[:500], k=10)["results"]
    within = call(ctx_for(alert.doc_id), "find_similar_incidents", description=alert.body[:500], k=10)["results"]

    assert alert.doc_id in {r["doc_id"] for r in without}  # the lure exists...
    assert alert.doc_id not in {r["doc_id"] for r in within}  # ...and is removed during an investigation


def test_a_cascades_postmortem_is_hidden_while_its_incident_is_being_investigated(s_documents, s_ctx, ctx_for):
    alert = next(d for d in s_documents if d.doc_id.startswith("alert-cascade-"))
    postmortem_id = alert.doc_id.replace("alert-", "postmortem-", 1)
    postmortem = next(d for d in s_documents if d.doc_id == postmortem_id)

    without = call(s_ctx, "search_postmortems", query=postmortem.body[:500], k=5)["results"]
    within = call(ctx_for(alert.doc_id), "search_postmortems", query=postmortem.body[:500], k=5)["results"]

    assert postmortem_id in {r["doc_id"] for r in without}
    assert postmortem_id not in {r["doc_id"] for r in within}


def test_exclusion_also_applies_to_the_cosine_signals(s_documents, s_ctx, ctx_for):
    alert = next(d for d in s_documents if d.doc_type == "alert")
    query = alert.body[:500]

    before = call(s_ctx, "find_similar_incidents", description=query)["top1_cosine_similarity"]
    during = call(ctx_for(alert.doc_id), "find_similar_incidents", description=query)["top1_cosine_similarity"]

    assert during < before  # the incident's own near-identical text no longer sets the top score


def test_the_runbook_an_incident_needs_is_not_hidden(s_documents, ctx_for):
    alert = next(d for d in s_documents if d.metadata.get("has_matching_runbook") and d.doc_type == "alert")
    rows = call(ctx_for(alert.doc_id), "search_runbooks", query=alert.body[:500], k=10)["results"]

    assert alert.metadata["correct_runbook"] in {r["doc_id"] for r in rows}


@pytest.mark.parametrize("tool, arg", [("search_runbooks", "query"), ("search_postmortems", "query"), ("find_similar_incidents", "description")])
def test_result_rows_carry_only_documented_fields_and_no_ground_truth(s_ctx, tool, arg):
    rows = call(s_ctx, tool, **{arg: "error rate elevated", "k": 5})["results"]

    for row in rows:
        assert set(row) - {"section"} == ROW_KEYS
        assert not GROUND_TRUTH_KEYS & set(row)


# ------------------------------------------------------------------- validation


@pytest.mark.parametrize("k", [0, 11, -3])
def test_k_is_bounded(s_ctx, k):
    with pytest.raises(ToolError, match="'k'"):
        call(s_ctx, "search_runbooks", query="latency", k=k)


@pytest.mark.parametrize("query", ["", "ab", "x" * 501])
def test_the_query_length_is_bounded(s_ctx, query):
    with pytest.raises(ToolError, match="query"):
        call(s_ctx, "search_runbooks", query=query)


def test_find_similar_incidents_takes_description_not_query(s_ctx):
    with pytest.raises(ToolError, match="unknown argument"):
        call(s_ctx, "find_similar_incidents", query="latency")
