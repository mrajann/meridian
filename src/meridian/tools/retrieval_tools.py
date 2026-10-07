"""Tools that search the indexed corpus: runbooks, postmortems, past incidents.

All three return the same score fields, labelled for what they are. The
ranking comes from hybrid search (vector + BM25 keyword), whose score is
min-max normalized *per query* and so cannot say how good a match is. Every
result therefore also carries the raw vector cosine similarity (absolute
scale), and the response carries the top-1 cosine and the gap to the second
hit -- the signals the retrieval evaluation (reports/retrieval_eval.md)
measured for telling "found it" from "found nothing".
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from meridian.indexing.store import Hit, build_filter
from meridian.retrieval import FUSION_DEPTH
from meridian.tools.context import ToolContext
from meridian.tools.registry import tool
from meridian.tools.types import SearchText

SCORE_GUIDE = {
    "cosine_similarity": (
        "Raw vector cosine similarity between your query and this result's text, -1 to 1 (typically 0.3-0.8 "
        "here). Absolute scale: comparable across results, queries and calls."
    ),
    "fused_score": (
        "Hybrid (vector + keyword) ranking score, min-max normalized per query to 0-4. Use it only to order "
        "results within this response; its value says nothing about match quality and is not comparable "
        "between queries."
    ),
    "top1_cosine_similarity": "Cosine similarity of the best document by vector ranking alone.",
    "gap_to_second_hit": (
        "Top-1 cosine minus top-2 cosine, by vector ranking over distinct documents. A large gap means one "
        "clear leader; a small gap means several documents match about equally well."
    ),
}


def _best_chunk_per_document(hits: list[Hit], excluded: frozenset[str]) -> list[Hit]:
    seen: set[str] = set(excluded)
    kept = []
    for hit in hits:
        if hit.doc_id not in seen:
            seen.add(hit.doc_id)
            kept.append(hit)
    return kept


def _search(ctx: ToolContext, query: str, k: int, doc_type: str | list[str]) -> dict[str, Any]:
    where = build_filter(doc_type=doc_type)
    retriever = ctx.retriever
    excluded = ctx.excluded_doc_ids

    fused = _best_chunk_per_document(
        retriever.search(query, k=min(max(k * 4, FUSION_DEPTH), 2 * FUSION_DEPTH), where=where, mode="hybrid"),
        excluded,
    )[:k]
    by_vector = retriever.search(query, k=FUSION_DEPTH, where=where, mode="vector")
    vector_docs = _best_chunk_per_document(by_vector, excluded)

    cosine = {hit.chunk_id: hit.score for hit in by_vector}
    missing = [hit.chunk_id for hit in fused if hit.chunk_id not in cosine]
    cosine.update(retriever.vector_index.cosine_similarities(query, missing))

    results = []
    for rank, hit in enumerate(fused, start=1):
        row: dict[str, Any] = {
            "rank": rank,
            "doc_id": hit.doc_id,
            "doc_type": hit.metadata["doc_type"],
            "title": hit.metadata["title"],
            "services": hit.metadata.get("services", []),
            "cosine_similarity": round(cosine[hit.chunk_id], 4),
            "fused_score": round(hit.score, 4),
            "text": hit.text,
        }
        if "section" in hit.metadata:
            row["section"] = hit.metadata["section"]
        results.append(row)

    return {
        "query": query,
        "results": results,
        "top1_cosine_similarity": round(vector_docs[0].score, 4) if vector_docs else None,
        "gap_to_second_hit": round(vector_docs[0].score - vector_docs[1].score, 4) if len(vector_docs) > 1 else None,
        "score_guide": SCORE_GUIDE,
    }


@tool
def search_runbooks(
    ctx: ToolContext,
    query: SearchText,
    k: Annotated[int, Field(ge=1, le=10)] = 5,
) -> dict:
    """Search the runbook library for documented procedures that address a symptom, failure mode, or alert.

    Use this first when you have an alert or symptom and want the documented response. Describe the failure in
    plain words and include the affected service name, e.g. "checkout-api requests stalling while waiting on a
    database connection" -- results come from a hybrid of semantic and keyword matching, so the failure phrase
    and the service name both help. Runbooks often word a condition differently from the alert that triggers
    them ("connection pool exhausted" in the alert, "database connections maxed out" in the runbook), so if the
    first query finds nothing convincing, rephrase the symptom before concluding no runbook exists.

    Do not use this for what happened in past incidents (use search_postmortems or find_similar_incidents) or for
    the current state of a system (use query_metrics).

    How to read the results: each result includes its full text -- read it and confirm it actually addresses the
    symptom, because both scores are weak evidence on their own (in evaluation, neither top-1 cosine nor the gap
    to the second hit cleanly separated real matches from missing ones). Two similar-looking runbooks can differ
    only in the root cause they assume, so check which cause the text names. A runbook can also be stale: if it
    tells you to operate a service that get_service reports as not found, it describes a decommissioned system
    and must not be followed. If nothing returned addresses the symptom, report that no matching runbook was
    found; do not present the nearest one as the answer.

    Args:
        query: The symptom or failure to find a procedure for, in plain words, ideally naming the service.
        k: How many runbooks to return, 1 to 10. The default of 5 is usually enough; use more only when the
            first results are all near-duplicates.

    Returns:
        results (rank, doc_id, title, services, cosine_similarity, fused_score, text per runbook),
        top1_cosine_similarity and gap_to_second_hit for the whole query, and a score_guide explaining each
        score field.
    """
    return _search(ctx, query, k, "runbook")


@tool
def search_postmortems(
    ctx: ToolContext,
    query: SearchText,
    k: Annotated[int, Field(ge=1, le=10)] = 5,
) -> dict:
    """Search past incident postmortems for what went wrong before: root causes, timelines, and action items.

    Use this to check whether the failure you are seeing has happened before and what its root cause turned out
    to be, especially when symptoms are spread across several services and you suspect one shared cause (past
    cascades are written up as a single postmortem naming the root service and every affected one). Describe the
    symptoms or the suspected cause in plain words, e.g. "writes refused and many services erroring at once".

    Do not use this to find the procedure for fixing something (use search_runbooks), and do not treat a
    postmortem as proof about the current incident: it shows a plausible cause that has occurred before, which
    you still need to confirm against current metrics.

    Each result is the best-matching section of one postmortem (Summary, Root cause, or Action items, named in
    `section`); a postmortem appears at most once. As with all retrieval here, read the text rather than
    trusting either score: cosine_similarity is the raw, absolute similarity, and fused_score only orders results
    within this response.

    Args:
        query: The symptoms, affected services, or suspected cause to look for in past incidents.
        k: How many postmortems to return, 1 to 10.

    Returns:
        results (rank, doc_id, title, services, section, cosine_similarity, fused_score, text per postmortem),
        top1_cosine_similarity and gap_to_second_hit for the whole query, and a score_guide.
    """
    return _search(ctx, query, k, "postmortem")


@tool
def find_similar_incidents(
    ctx: ToolContext,
    description: SearchText,
    k: Annotated[int, Field(ge=1, le=10)] = 5,
) -> dict:
    """Find past incidents that look like the one you are investigating, across both fired alerts and postmortems.

    Use this early, with a short description of what you are observing (the alert text, the affected services,
    the key symptom), to see whether this has happened before. Results mix two kinds of record, shown in
    `doc_type`: "alert" (what was observed when an incident fired) and "postmortem" (what it turned out to be).
    A similar past alert tells you the pattern recurs; follow up with search_postmortems for its cause or
    search_runbooks for its fix. The incident you are currently investigating is excluded.

    Do not use this to look up a procedure (use search_runbooks). Similar symptoms do not guarantee a similar
    cause: two incidents can look alike and differ in root cause, so treat a match as a hypothesis to check.

    Read the text of each result; cosine_similarity is the raw absolute similarity (comparable across queries)
    while fused_score only orders results within this response and carries no match-quality meaning.

    Args:
        description: What you are observing, in plain words: symptom, affected services, and anything distinctive.
        k: How many past incidents to return, 1 to 10.

    Returns:
        results (rank, doc_id, doc_type, title, services, cosine_similarity, fused_score, text per record),
        top1_cosine_similarity and gap_to_second_hit for the whole query, and a score_guide.
    """
    return _search(ctx, description, k, ["alert", "postmortem"])
