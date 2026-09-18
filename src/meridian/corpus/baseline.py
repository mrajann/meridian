"""Baseline (non-adversarial) reference-material generation: broad coverage
across all 41 services so retrieval has more to work with than just the
adversarial anchors. Template-driven, deterministic, same mechanism as the
adversarial generators but with none of their special structure."""

from __future__ import annotations

from meridian.catalog import ServiceEntry
from meridian.corpus.models import CorpusDocument
from meridian.corpus.taxonomy import CATEGORY_INFO, FRAGILE_SERVICES, pool

# ============================================================
# Body renderers
# ============================================================


def _runbook_body(service: str, category: str, catalog: dict[str, ServiceEntry]) -> str:
    info = CATEGORY_INFO[category]
    entry = catalog[service]
    dep_clause = (
        f" Check {entry.depends_on[0]} first -- {service} depends on it directly." if entry.depends_on else ""
    )
    return (
        f"{service} is showing {info['symptom']}.{dep_clause} Check the {service} dashboard and "
        f"recent deploys via ci-pipeline before assuming the fault is in {service} itself.\n\n"
        f"Likely cause: {info['cause']}.\n\n"
        f"Fix: confirm the cause above against current metrics before acting. Resolve at the source "
        f"rather than restarting {service} -- a restart will not fix {category.replace('_', ' ')} if "
        f"the underlying condition is still present.\n\n"
        f"Blast radius: {entry.blast_radius}"
    )


def _postmortem_body(service: str, category: str, incident_number: int) -> str:
    info = CATEGORY_INFO[category]
    recurrence = f" This is recorded incident #{incident_number} of this type for {service}." if incident_number > 1 else ""
    return (
        f"Summary: {service} experienced {info['symptom']}.{recurrence}\n\n"
        f"Root cause: {info['cause']}.\n\n"
        f"Action items: add direct alerting on this failure mode for {service} rather than relying on "
        f"downstream symptoms to surface it."
    )


def _alert_body(service: str, category: str) -> str:
    info = CATEGORY_INFO[category]
    return (
        f"{service}: {info['symptom']}. Onset was within the last monitoring window -- investigate "
        f"before it breaches SLO further."
    )


# ============================================================
# Deterministic weighted round-robin over (service, category) pairs
# ============================================================


def _weighted_order(weights: dict[str, int], length: int) -> list[str]:
    counts = {k: 0 for k in weights}
    order = []
    for _ in range(length):
        pick = min(weights, key=lambda k: (counts[k] / weights[k], k))
        order.append(pick)
        counts[pick] += 1
    return order


def _bulk_pairs(
    catalog: dict[str, ServiceEntry],
    count: int,
    weights: dict[str, int],
    exclude: set[tuple[str, str]],
    allow_repeats: bool = False,
) -> list[tuple[str, str]]:
    service_order = _weighted_order(weights, count * 4)
    pool_index = {s: 0 for s in weights}
    seen: set[tuple[str, str]] = set(exclude)
    pairs: list[tuple[str, str]] = []

    for service in service_order:
        if len(pairs) >= count:
            break
        svc_pool = pool(catalog, service)
        idx = pool_index[service]
        if idx >= len(svc_pool):
            if not allow_repeats:
                continue
            pool_index[service] = 0
            idx = 0
        category = svc_pool[idx]
        pool_index[service] += 1
        key = (service, category)
        if key in seen and not allow_repeats:
            continue
        seen.add(key)
        pairs.append(key)

    return pairs


def generate_baseline_runbooks(
    catalog: dict[str, ServiceEntry], count: int, exclude: set[tuple[str, str]]
) -> list[CorpusDocument]:
    weights = {s: 1 for s in catalog}
    pairs = _bulk_pairs(catalog, count, weights, exclude, allow_repeats=False)
    return [
        CorpusDocument(
            doc_id=f"runbook-baseline-{service}-{category}",
            doc_type="runbook",
            title=f"{service}: {category.replace('_', ' ')}",
            services=[service],
            metadata={"root_cause_category": category},
            body=_runbook_body(service, category, catalog),
        )
        for service, category in pairs
    ]


def generate_baseline_postmortems(
    catalog: dict[str, ServiceEntry], count: int, fragile_target: int, exclude: set[tuple[str, str]]
) -> list[CorpusDocument]:
    fragile_weights = {s: 1 for s in FRAGILE_SERVICES}
    nonfragile_weights = {s: 1 for s in catalog if s not in FRAGILE_SERVICES}
    pairs = [
        *_bulk_pairs(catalog, fragile_target, fragile_weights, exclude, allow_repeats=True),
        *_bulk_pairs(catalog, count - fragile_target, nonfragile_weights, exclude, allow_repeats=True),
    ]

    seen_counts: dict[tuple[str, str], int] = {}
    docs = []
    for service, category in pairs:
        key = (service, category)
        seen_counts[key] = seen_counts.get(key, 0) + 1
        n = seen_counts[key]
        suffix = f"-{n}" if n > 1 else ""
        docs.append(
            CorpusDocument(
                doc_id=f"postmortem-baseline-{service}-{category}{suffix}",
                doc_type="postmortem",
                title=f"Postmortem: {service} {category.replace('_', ' ')}" + (f" (incident #{n})" if n > 1 else ""),
                services=[service],
                metadata={
                    "root_cause_service": service,
                    "root_cause_category": category,
                    "affected_services": [],
                    "fragile_service": service if service in FRAGILE_SERVICES else None,
                },
                body=_postmortem_body(service, category, n),
            )
        )
    return docs


def generate_baseline_alerts(
    catalog: dict[str, ServiceEntry],
    count: int,
    fragile_target: int,
    runbook_lookup: dict[tuple[str, str], str],
    exclude: set[tuple[str, str]],
) -> list[CorpusDocument]:
    used_counts: dict[tuple[str, str], int] = dict.fromkeys(exclude, 1)

    def _group(services: list[str], target: int) -> list[CorpusDocument]:
        order = _weighted_order({s: 1 for s in services}, max(target * 8, 8))
        docs: list[CorpusDocument] = []
        for service in order:
            if len(docs) >= target:
                break
            candidates = [c for c in pool(catalog, service) if (service, c) in runbook_lookup]
            if not candidates:
                continue
            category = min(candidates, key=lambda c: used_counts.get((service, c), 0))
            key = (service, category)
            n = used_counts.get(key, 0) + 1
            used_counts[key] = n
            suffix = f"-{n}" if n > 1 else ""
            docs.append(
                CorpusDocument(
                    doc_id=f"alert-baseline-{service}-{category}{suffix}",
                    doc_type="alert",
                    title=f"{service}: {CATEGORY_INFO[category]['symptom']}" + (f" (recurrence #{n})" if n > 1 else ""),
                    services=[service],
                    metadata={
                        "root_cause_service": service,
                        "root_cause_category": category,
                        "correct_runbook": runbook_lookup[key],
                        "has_matching_runbook": True,
                        "fragile_service": service if service in FRAGILE_SERVICES else None,
                    },
                    body=_alert_body(service, category),
                )
            )
        return docs

    return [
        *_group(sorted(FRAGILE_SERVICES), fragile_target),
        *_group(sorted(s for s in catalog if s not in FRAGILE_SERVICES), count - fragile_target),
    ]


def build_runbook_lookup(runbooks: list[CorpusDocument]) -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}
    for doc in runbooks:
        category = doc.metadata.get("root_cause_category", "")
        if "__" in category or category == "stale":
            continue  # near-dup / stale runbooks are deliberately not a clean match target
        for service in doc.services:
            key = (service, category)
            if key not in lookup:
                lookup[key] = doc.doc_id
    return lookup


def generate_chat_transcripts(alerts: list[CorpusDocument], count: int) -> list[CorpusDocument]:
    speakers = ["priya", "dev", "maya", "sam", "jules", "arun", "lin", "kai", "noor", "theo"]
    docs = []
    chosen = sorted(alerts, key=lambda a: a.doc_id)[:count]
    for i, alert in enumerate(chosen):
        service = alert.services[0]
        category = alert.metadata.get("root_cause_category", "unknown")
        symptom = CATEGORY_INFO.get(category, {}).get("symptom", "a symptom")
        s1, s2 = speakers[i % len(speakers)], speakers[(i + 1) % len(speakers)]
        if alert.metadata.get("has_matching_runbook"):
            resolution = (
                f"[+9m] @{s1}: found the runbook for this, running the fix now\n"
                f"[+14m] @{s2}: confirmed, back to normal"
            )
        else:
            resolution = (
                f"[+9m] @{s1}: couldn't find a runbook for this exact symptom\n"
                f"[+15m] @{s2}: tracked it down manually, let's write a runbook once this is resolved"
            )
        docs.append(
            CorpusDocument(
                doc_id=f"chat-{alert.doc_id}",
                doc_type="chat_transcript",
                title=f"#incidents: {service} alert discussion",
                services=[service],
                metadata={"root_cause_service": alert.metadata.get("root_cause_service")},
                body=(
                    f"[+0m] @{s1}: paged for {service}, {symptom}\n"
                    f"[+2m] @{s2}: looking now\n"
                    f"[+4m] @{s1}: can confirm, checking dependencies\n"
                    f"{resolution}"
                ),
            )
        )
    return docs


def generate_catalog_documents(catalog: dict[str, ServiceEntry], services: list[str]) -> list[CorpusDocument]:
    docs = []
    for name in services:
        entry = catalog[name]
        body = (
            f"{entry.description}\n\n"
            f"Owner: {entry.owner}. Tier: {entry.tier}.\n"
            f"Depends on: {', '.join(entry.depends_on) or 'nothing'}.\n"
            f"Depended on by: {', '.join(entry.depended_on_by) or 'nothing'}.\n"
            f"Availability target: {entry.slo.availability}%.\n"
            f"Blast radius: {entry.blast_radius}"
        )
        docs.append(
            CorpusDocument(
                doc_id=f"catalog-entry-{entry.name}",
                doc_type="catalog_entry",
                title=f"Service catalog: {entry.name}",
                services=[entry.name],
                metadata={"tier": entry.tier, "owner": entry.owner},
                body=body,
            )
        )
    return docs
