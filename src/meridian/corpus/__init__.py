"""Synthetic incident corpus: documents, generation, and disk I/O.

generate_corpus() builds the corpus in two layers:

1. Adversarial (meridian.corpus.adversarial) -- each of the five cases from
   spec section 3 has its own generator function taking an explicit target
   count. These run first and their document counts are the ones that
   matter for evaluating retrieval against adversarial cases.
2. Baseline (meridian.corpus.baseline) -- template-generated reference
   material filling out broad service coverage, built around whatever the
   adversarial layer didn't already claim.
"""

from __future__ import annotations

from collections import defaultdict

from meridian.catalog import ServiceEntry
from meridian.corpus.adversarial import (
    generate_cascading_failure_sets,
    generate_near_duplicate_pairs,
    generate_no_matching_runbook_incidents,
    generate_stale_runbooks,
    generate_vocabulary_mismatch_cases,
)
from meridian.corpus.baseline import (
    build_runbook_lookup,
    generate_baseline_alerts,
    generate_baseline_postmortems,
    generate_baseline_runbooks,
    generate_catalog_documents,
    generate_chat_transcripts,
)
from meridian.corpus.models import CORPUS_DIR, CorpusDocument, load_corpus, write_corpus
from meridian.corpus.taxonomy import DECOMMISSIONED_SERVICES, FRAGILE_SERVICES, pool

# Target counts. Adversarial counts are the ones the spec/verification tests
# hold to a floor; baseline counts just round out reference coverage.
NEAR_DUPLICATE_PAIR_COUNT = 28
VOCABULARY_MISMATCH_COUNT = 28
NO_MATCHING_RUNBOOK_COUNT = 15
CASCADING_FAILURE_SET_COUNT = 13
STALE_RUNBOOK_COUNT = 10

BASELINE_RUNBOOK_COUNT = 90
BASELINE_POSTMORTEM_COUNT = 90
BASELINE_POSTMORTEM_FRAGILE_TARGET = 51
BASELINE_ALERT_COUNT = 40
BASELINE_ALERT_FRAGILE_TARGET = 26
CHAT_TRANSCRIPT_COUNT = 35
CATALOG_DOCUMENT_COUNT = 20


def _all_pairs(catalog: dict[str, ServiceEntry]) -> list[tuple[str, str]]:
    return [(s, c) for s in sorted(catalog) for c in pool(catalog, s)]


def _reserve_no_match_pairs(
    catalog: dict[str, ServiceEntry], already_used: set[tuple[str, str]], count: int
) -> list[tuple[str, str]]:
    """Round-robins one category per service (in alphabetical service order)
    across pairs not already claimed, so the reserved set spreads across many
    services rather than piling onto whichever sorts first."""
    by_service: dict[str, list[str]] = defaultdict(list)
    for service, category in _all_pairs(catalog):
        if (service, category) not in already_used:
            by_service[service].append(category)

    services = sorted(by_service)
    picked: list[tuple[str, str]] = []
    depth = 0
    while len(picked) < count:
        progressed = False
        for service in services:
            if depth < len(by_service[service]):
                picked.append((service, by_service[service][depth]))
                progressed = True
                if len(picked) >= count:
                    break
        if not progressed:
            raise ValueError(f"ran out of unclaimed (service, category) pairs before reaching {count}")
        depth += 1
    return picked


def generate_corpus(catalog: dict[str, ServiceEntry]) -> list[CorpusDocument]:
    # --- Adversarial layer ---
    near_dup = generate_near_duplicate_pairs(catalog, count=NEAR_DUPLICATE_PAIR_COUNT)
    vocab_mismatch = generate_vocabulary_mismatch_cases(catalog, count=VOCABULARY_MISMATCH_COUNT)
    cascades = generate_cascading_failure_sets(catalog, count=CASCADING_FAILURE_SET_COUNT)
    stale = generate_stale_runbooks(DECOMMISSIONED_SERVICES, count=STALE_RUNBOOK_COUNT)

    adversarial_runbooks = [
        d for d in [*near_dup, *vocab_mismatch, *cascades, *stale] if d.doc_type == "runbook"
    ]

    # Pairs a runbook already exists for -- reserved for "no matching
    # runbook" must avoid these (otherwise a no-match alert could claim "no
    # runbook exists" for a pair the cascade generator just created one
    # for), and baseline runbook generation should too (near-dup's are
    # suffixed "category__id" so can't collide by id, but are excluded
    # anyway to avoid a redundant plain-category runbook sitting right next
    # to a near-duplicate pair for the same service+category).
    claimed_pairs = {
        (doc.services[0], doc.metadata["root_cause_category"].split("__")[0]) for doc in adversarial_runbooks
    }

    no_match_pairs = _reserve_no_match_pairs(catalog, claimed_pairs, NO_MATCHING_RUNBOOK_COUNT)
    no_match = generate_no_matching_runbook_incidents(catalog, no_match_pairs, count=NO_MATCHING_RUNBOOK_COUNT)

    exclude_from_baseline_runbooks = claimed_pairs | set(no_match_pairs)

    # --- Baseline layer ---
    baseline_runbooks = generate_baseline_runbooks(catalog, BASELINE_RUNBOOK_COUNT, exclude_from_baseline_runbooks)
    baseline_postmortems = generate_baseline_postmortems(
        catalog, BASELINE_POSTMORTEM_COUNT, BASELINE_POSTMORTEM_FRAGILE_TARGET, exclude=set()
    )

    all_runbooks = [*adversarial_runbooks, *baseline_runbooks]
    runbook_lookup = build_runbook_lookup(all_runbooks)
    baseline_alerts = generate_baseline_alerts(
        catalog,
        BASELINE_ALERT_COUNT,
        BASELINE_ALERT_FRAGILE_TARGET,
        runbook_lookup,
        exclude=set(),
    )

    all_alerts_so_far = [
        *[d for d in near_dup if d.doc_type == "alert"],
        *[d for d in vocab_mismatch if d.doc_type == "alert"],
        *[d for d in cascades if d.doc_type == "alert"],
        *no_match,
        *baseline_alerts,
    ]
    chats = generate_chat_transcripts(all_alerts_so_far, CHAT_TRANSCRIPT_COUNT)

    catalog_services = sorted(catalog)[:CATALOG_DOCUMENT_COUNT]
    catalog_docs = generate_catalog_documents(catalog, catalog_services)

    return [
        *near_dup,
        *vocab_mismatch,
        *cascades,
        *stale,
        *no_match,
        *baseline_runbooks,
        *baseline_postmortems,
        *baseline_alerts,
        *chats,
        *catalog_docs,
    ]


__all__ = [
    "BASELINE_ALERT_COUNT",
    "BASELINE_ALERT_FRAGILE_TARGET",
    "BASELINE_POSTMORTEM_COUNT",
    "BASELINE_POSTMORTEM_FRAGILE_TARGET",
    "BASELINE_RUNBOOK_COUNT",
    "CASCADING_FAILURE_SET_COUNT",
    "CATALOG_DOCUMENT_COUNT",
    "CHAT_TRANSCRIPT_COUNT",
    "CORPUS_DIR",
    "CorpusDocument",
    "DECOMMISSIONED_SERVICES",
    "FRAGILE_SERVICES",
    "NEAR_DUPLICATE_PAIR_COUNT",
    "NO_MATCHING_RUNBOOK_COUNT",
    "STALE_RUNBOOK_COUNT",
    "VOCABULARY_MISMATCH_COUNT",
    "generate_corpus",
    "load_corpus",
    "write_corpus",
]
