"""First-class generators for each adversarial case in spec section 3.

Each function takes a target count and produces exactly that many instances
of its case, verified post-generation by tests against the real generated
output -- not seeded as a handful of hand-authored examples and left for
bulk/baseline generation to (not) reproduce at scale.
"""

from __future__ import annotations

from meridian.catalog import ServiceEntry
from meridian.corpus.models import CorpusDocument
from meridian.corpus.synonyms import SYNONYM_PAIRS
from meridian.corpus.taxonomy import CATEGORY_INFO, MECHANISM_PAIRS, FRAGILE_SERVICES, pool, services_with_category
from meridian.graph import DependencyGraph

# ============================================================
# 1. Near-duplicate runbook pairs
# ============================================================


def _dependency_blame_candidates(catalog: dict[str, ServiceEntry]) -> list[str]:
    return sorted((s for s, e in catalog.items() if len(e.depends_on) >= 2), key=lambda s: -len(catalog[s].depends_on))


def generate_near_duplicate_pairs(catalog: dict[str, ServiceEntry], count: int = 28) -> list[CorpusDocument]:
    """`count` pairs of near-duplicate runbooks (2*count runbook docs) plus
    one alert per pair pointing at the correct half. Two generation patterns:

    - a service with >=2 dependencies: the pair blames two different real
      dependencies for the same symptom (e.g. "is it the database or the
      payment processor").
    - a service with <2 dependencies (can't blame a dependency): the pair
      blames two different *mechanisms* behind the same failure category on
      the service itself (e.g. two different reasons a disk fills up).
    """
    docs: list[CorpusDocument] = []

    dep_candidates = _dependency_blame_candidates(catalog)
    # Prioritize the fragile services and a couple of other well-known hubs
    # so they get a near-duplicate pair even though they have <2 dependencies.
    # Category chosen explicitly per service rather than derived from the
    # team's whole pool, since e.g. redis-cache inherits data-platform's pool
    # (which includes disk_full) but "disk full" doesn't fit an in-memory cache.
    mechanism_assignments = [
        ("postgres-primary", "disk_full"),
        ("redis-cache", "memory_leak"),
        ("secrets-manager", "certificate_expiry"),
    ]

    plan: list[tuple[str, str | None]] = []
    for service in dep_candidates:
        plan.append((service, None))  # None => dependency-blame pattern
    for service, category in mechanism_assignments:
        if service in catalog:
            plan.append((service, category))

    plan = plan[:count]
    assert len(plan) == count, f"only {len(plan)} services available for {count} near-duplicate pairs"

    for service, mechanism_category in plan:
        entry = catalog[service]

        if mechanism_category is None:
            dep_a, dep_b = entry.depends_on[0], entry.depends_on[1]
            category = pool(catalog, service)[0]
            symptom = CATEGORY_INFO[category]["symptom"]
            suffix_a, suffix_b = dep_a, dep_b
            cause_a = f"{dep_a} is degraded or unavailable, so {service}'s calls to it are failing or timing out"
            fix_a = f"check {dep_a} health directly before touching {service} itself"
            cause_b = f"{dep_b} is degraded or unavailable, so {service}'s calls to it are failing or timing out"
            fix_b = f"check {dep_b} health directly before touching {service} itself"
            category_a, category_b = f"{category}__{suffix_a}", f"{category}__{suffix_b}"
        else:
            m = MECHANISM_PAIRS[mechanism_category]
            symptom = CATEGORY_INFO[mechanism_category]["symptom"]
            suffix_a, suffix_b = m["id_a"], m["id_b"]
            cause_a, fix_a = m["cause_a"], m["fix_a"]
            cause_b, fix_b = m["cause_b"], m["fix_b"]
            category_a, category_b = f"{mechanism_category}__{suffix_a}", f"{mechanism_category}__{suffix_b}"

        shared_intro = (
            f"{service} is showing {symptom}. Check the {service} dashboard for error rate and "
            f"latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.\n\n"
        )
        runbook_a = CorpusDocument(
            doc_id=f"runbook-{service}-{suffix_a}",
            doc_type="runbook",
            title=f"{service}: {symptom} ({suffix_a} root cause)",
            services=[service],
            metadata={"root_cause_category": category_a},
            body=shared_intro + f"Root cause: {cause_a}.\n\nFix: {fix_a}.",
        )
        runbook_b = CorpusDocument(
            doc_id=f"runbook-{service}-{suffix_b}",
            doc_type="runbook",
            title=f"{service}: {symptom} ({suffix_b} root cause)",
            services=[service],
            metadata={"root_cause_category": category_b},
            body=shared_intro + f"Root cause: {cause_b}.\n\nFix: {fix_b}.",
        )
        alert = CorpusDocument(
            doc_id=f"alert-near-dup-{service}",
            doc_type="alert",
            title=f"{service}: {symptom}",
            services=[service],
            metadata={
                "root_cause_service": service,
                "root_cause_category": category_a,
                "correct_runbook": runbook_a.doc_id,
                "has_matching_runbook": True,
                "fragile_service": service if service in FRAGILE_SERVICES else None,
                "adversarial_case": "near_duplicate_pair",
            },
            body=f"{service}: {symptom}. Onset within the last monitoring window.",
        )
        docs.extend([runbook_a, runbook_b, alert])

    return docs


# ============================================================
# 2. Vocabulary-mismatch cases
# ============================================================


def generate_vocabulary_mismatch_cases(catalog: dict[str, ServiceEntry], count: int = 28) -> list[CorpusDocument]:
    """`count` alert/runbook pairs. Each pair describes the same underlying
    condition using two different phrasings from meridian.corpus.synonyms --
    the alert uses one, the runbook uses the other, and neither phrase
    appears in the other's document. Bodies are deliberately minimal
    (not built from the shared CATEGORY_INFO cause text) so the synonym
    phrases are the only thing determining lexical overlap.
    """
    assert count <= len(SYNONYM_PAIRS), f"only {len(SYNONYM_PAIRS)} synonym pairs defined, need {count}"

    docs: list[CorpusDocument] = []
    service_cursor: dict[str, int] = {}

    for i in range(count):
        pair = SYNONYM_PAIRS[i]
        category = pair["category"]
        eligible = services_with_category(catalog, category)
        idx = service_cursor.get(category, 0) % len(eligible)
        service = eligible[idx]
        service_cursor[category] = idx + 1

        runbook_id = f"runbook-vocab-{service}-{category}-{i}"
        alert_id = f"alert-vocab-{service}-{category}-{i}"

        docs.append(
            CorpusDocument(
                doc_id=runbook_id,
                doc_type="runbook",
                title=f"{service}: {pair['runbook_phrase']}",
                services=[service],
                metadata={"root_cause_category": category, "adversarial_case": "vocabulary_mismatch"},
                body=(
                    f"{service} runbook.\n\n"
                    f"Symptom: {pair['runbook_phrase']}.\n\n"
                    f"Fix: address the underlying condition directly on {service} -- a restart alone "
                    f"will not resolve this."
                ),
            )
        )
        docs.append(
            CorpusDocument(
                doc_id=alert_id,
                doc_type="alert",
                title=f"{service}: {pair['alert_phrase']}",
                services=[service],
                metadata={
                    "root_cause_service": service,
                    "root_cause_category": category,
                    "correct_runbook": runbook_id,
                    "has_matching_runbook": True,
                    "fragile_service": service if service in FRAGILE_SERVICES else None,
                    "adversarial_case": "vocabulary_mismatch",
                },
                body=f"{service} alert: {pair['alert_phrase']}. Investigate before it breaches SLO further.",
            )
        )

    return docs


# ============================================================
# 3. No-matching-runbook incidents
# ============================================================


def generate_no_matching_runbook_incidents(
    catalog: dict[str, ServiceEntry], reserved_pairs: list[tuple[str, str]], count: int = 15
) -> list[CorpusDocument]:
    """`count` alerts for (service, category) pairs in `reserved_pairs` --
    combinations the caller has held back from every runbook generator, so
    "no matching runbook" is a real, verifiable property of the corpus
    rather than an assumption. See build_corpus() for how the reservation
    is made and tests/test_corpus_adversarial.py for the verification.
    """
    assert len(reserved_pairs) >= count, f"need {count} reserved (service, category) pairs, got {len(reserved_pairs)}"

    docs = []
    for service, category in reserved_pairs[:count]:
        docs.append(
            CorpusDocument(
                doc_id=f"alert-no-match-{service}-{category}",
                doc_type="alert",
                title=f"{service}: {CATEGORY_INFO[category]['symptom']}",
                services=[service],
                metadata={
                    "root_cause_service": service,
                    "root_cause_category": category,
                    "correct_runbook": None,
                    "has_matching_runbook": False,
                    "fragile_service": service if service in FRAGILE_SERVICES else None,
                    "adversarial_case": "no_matching_runbook",
                },
                body=(
                    f"{service}: {CATEGORY_INFO[category]['symptom']}. Onset within the last monitoring "
                    f"window -- investigate before it breaches SLO further."
                ),
            )
        )
    return docs


# ============================================================
# 4. Cascading-failure sets
# ============================================================

# (hub service, how many non-overlapping 6-service cascades it can support)
_CASCADE_HUBS = [
    "postgres-primary",
    "redis-cache",
    "postgres-replica",
    "secrets-manager",
    "feature-flags",
    "inventory-service",
    "pricing-engine",
    "kafka-broker",
]


def generate_cascading_failure_sets(catalog: dict[str, ServiceEntry], count: int = 13) -> list[CorpusDocument]:
    """`count` (postmortem, alert) pairs, each with >=6 services that are
    *real* transitive dependents of some hub service (verified against
    DependencyGraph, not fabricated), non-overlapping within the same hub.
    postgres-primary is the spec's canonical example and has by far the most
    dependents, so it contributes the most sets; other well-connected
    services fill out the rest so 13 non-overlapping sets are achievable at
    all (postgres-primary alone only supports 4 before running out of
    distinct dependents).
    """
    graph = DependencyGraph(catalog)
    sets: list[tuple[str, list[str]]] = []
    for hub in _CASCADE_HUBS:
        dependents = sorted(graph.dependents(hub))
        for start in range(0, len(dependents) - 5, 6):
            if len(sets) >= count:
                break
            sets.append((hub, dependents[start : start + 6]))
        if len(sets) >= count:
            break

    assert len(sets) >= count, f"only {len(sets)} non-overlapping 6-service cascades available, need {count}"
    sets = sets[:count]

    docs = []
    runbook_for: dict[tuple[str, str], str] = {}
    for i, (hub, affected) in enumerate(sets):
        category = pool(catalog, hub)[i % len(pool(catalog, hub))]

        # One root-cause runbook per distinct (hub, category), shared across
        # any cascades that reuse it (a real corpus wouldn't have a separate
        # runbook per incident, just per failure mode) -- so the cascade
        # alert has a genuine match, distinct from the no-matching-runbook
        # adversarial case.
        runbook_id = runbook_for.get((hub, category))
        if runbook_id is None:
            runbook_id = f"runbook-cascade-root-cause-{hub}-{category}"
            runbook_for[(hub, category)] = runbook_id
            docs.append(
                CorpusDocument(
                    doc_id=runbook_id,
                    doc_type="runbook",
                    title=f"{hub}: {CATEGORY_INFO[category]['symptom']} (cascading)",
                    services=[hub],
                    metadata={"root_cause_category": category},
                    body=(
                        f"{hub} is showing {CATEGORY_INFO[category]['symptom']}. Because so many services "
                        f"depend on {hub} directly or transitively, this often presents as simultaneous "
                        f"errors across several unrelated-looking services rather than a single {hub} alert "
                        f"-- treat a burst of simultaneous cross-service errors as one {hub} incident, not "
                        f"several.\n\n"
                        f"Root cause: {CATEGORY_INFO[category]['cause']}.\n\n"
                        f"Fix: resolve the condition on {hub} directly; the downstream services will "
                        f"recover on their own once it does."
                    ),
                )
            )

        postmortem_id = f"postmortem-cascade-{hub}-{i}"
        docs.append(
            CorpusDocument(
                doc_id=postmortem_id,
                doc_type="postmortem",
                title=f"Postmortem: {hub} cascade ({CATEGORY_INFO[category]['symptom']})",
                services=[hub, *affected],
                metadata={
                    "root_cause_service": hub,
                    "root_cause_category": category,
                    "affected_services": affected,
                    "fragile_service": hub if hub in FRAGILE_SERVICES else None,
                    "adversarial_case": "cascading_failure",
                },
                body=(
                    f"Summary: {hub} experienced {CATEGORY_INFO[category]['symptom']}. This produced "
                    f"symptoms in {len(affected)} dependent services at once: {', '.join(affected)}.\n\n"
                    f"Root cause: {CATEGORY_INFO[category]['cause']}.\n\n"
                    f"On-call for several of the affected services were paged independently before the "
                    f"shared root cause on {hub} was identified -- this is one incident, not "
                    f"{len(affected)} separate ones.\n\n"
                    f"Action items: alert directly on {hub} rather than relying on downstream symptoms "
                    f"to surface a shared root cause."
                ),
            )
        )
        docs.append(
            CorpusDocument(
                doc_id=f"alert-cascade-{hub}-{i}",
                doc_type="alert",
                title=f"5xx spike across {len(affected)} services simultaneously",
                services=affected,
                metadata={
                    "root_cause_service": hub,
                    "root_cause_category": category,
                    "correct_runbook": runbook_id,
                    "has_matching_runbook": True,
                    "affected_services": affected,
                    "fragile_service": hub if hub in FRAGILE_SERVICES else None,
                    "adversarial_case": "cascading_failure",
                },
                body=(
                    f"Simultaneous error-rate increase across {', '.join(affected)}, all starting within "
                    f"the same 60-second window. All depend on {hub}, directly or transitively."
                ),
            )
        )
    return docs


# ============================================================
# 5. Stale runbooks
# ============================================================


def generate_stale_runbooks(decommissioned_services: list[str], count: int = 10) -> list[CorpusDocument]:
    """`count` runbooks referencing services in `decommissioned_services`,
    cycled round-robin so every name gets used roughly evenly."""
    angles = ["elevated error rate", "manual restart procedure", "scheduled maintenance window"]
    docs = []
    for i in range(count):
        name = decommissioned_services[i % len(decommissioned_services)]
        angle = angles[i % len(angles)]
        occurrence = i // len(decommissioned_services) + 1
        suffix = f"-{occurrence}" if occurrence > 1 else ""
        docs.append(
            CorpusDocument(
                doc_id=f"runbook-stale-{name}{suffix}",
                doc_type="runbook",
                title=f"{name}: {angle}",
                services=[name],
                metadata={"root_cause_category": "stale", "stale_reference": name, "adversarial_case": "stale_runbook"},
                body=(
                    f"If {name} shows {angle}, SSH into its hosts and check the application logs "
                    f"directly; restart via the legacy deploy tool if needed.\n\n"
                    f"[This runbook references a decommissioned service. {name} no longer exists in the "
                    f"current catalog.]"
                ),
            )
        )
    return docs
