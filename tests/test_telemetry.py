"""The synthetic world: determinism, scenarios built from corpus labels, the
metric signature of each failure category, and the deploy mix."""

import statistics
from collections import Counter
from datetime import timedelta

import pytest

from meridian.corpus.taxonomy import CATEGORY_INFO
from meridian.slo import burn_rate, error_budget_fraction
from meridian.telemetry import DEFAULT_NOW, METRICS, Telemetry, available_metrics, rng
from meridian.telemetry.metrics import CATEGORY_EFFECTS, Effect
from meridian.telemetry.scenario import ALWAYS_DEPLOY_CAUSED, SOMETIMES_DEPLOY_CAUSED

# ------------------------------------------------------------------------ rng


def test_rng_is_a_pure_function_of_its_keys():
    assert rng.unit("a", 1) == rng.unit("a", 1)
    assert rng.unit("a", 1) != rng.unit("a", 2)
    assert rng.gauss("x", 3) == rng.gauss("x", 3)


def test_rng_unit_is_in_the_half_open_unit_interval_and_roughly_uniform():
    values = [rng.unit("u", i) for i in range(4000)]

    assert all(0.0 <= v < 1.0 for v in values)
    assert abs(statistics.mean(values) - 0.5) < 0.03


def test_rng_gauss_is_roughly_standard_normal():
    values = [rng.gauss("g", i) for i in range(4000)]

    assert abs(statistics.mean(values)) < 0.08
    assert abs(statistics.stdev(values) - 1.0) < 0.08


def test_rng_uniform_respects_its_bounds():
    assert all(5.0 <= rng.uniform(5, 9, "b", i) < 9.0 for i in range(500))


# ------------------------------------------------------------------ scenarios


def test_a_scenario_exists_for_every_alert(s_scenarios, s_documents):
    alerts = {d.doc_id for d in s_documents if d.doc_type == "alert"}

    assert set(s_scenarios) == alerts and len(alerts) >= 100


def test_scenarios_are_deterministic(s_documents, s_catalog):
    from meridian.telemetry import build_scenarios

    assert build_scenarios(s_documents, s_catalog) == build_scenarios(s_documents, s_catalog)


def test_detection_comes_after_onset(s_scenarios):
    for sc in s_scenarios.values():
        assert timedelta(minutes=4) <= sc.now - sc.onset <= timedelta(minutes=14), sc.incident_id


def test_every_corpus_failure_category_has_an_effects_entry():
    assert set(CATEGORY_INFO) <= set(CATEGORY_EFFECTS)


def test_the_alerting_service_always_shows_symptoms_even_when_it_is_not_the_root(s_scenarios, s_documents):
    for doc in s_documents:
        if doc.doc_type == "alert":
            sc = s_scenarios[doc.doc_id]
            for service in doc.services:
                assert service == sc.root_cause_service or service in sc.symptomatic, doc.doc_id


def test_a_near_duplicate_alert_blames_the_dependency_its_correct_runbook_names(s_scenarios, s_documents, s_catalog):
    redirected = 0
    for doc in s_documents:
        if doc.doc_type == "alert" and doc.metadata.get("adversarial_case") == "near_duplicate_pair":
            service = doc.services[0]
            sc = s_scenarios[doc.doc_id]
            suffix = doc.metadata["root_cause_category"].partition("__")[2]
            if suffix in s_catalog[service].depends_on:
                redirected += 1
                assert sc.root_cause_service == suffix
                assert service in sc.symptomatic
            else:  # a mechanism pair (e.g. disk fills two different ways): the fault is on the service itself
                assert sc.root_cause_service == service
    assert redirected >= 20


def test_a_cascade_alerts_postmortem_is_excluded_from_retrieval(s_scenarios):
    sc = next(s for s in s_scenarios.values() if s.incident_id.startswith("alert-cascade-"))

    assert sc.incident_id in sc.excluded_doc_ids
    assert sc.incident_id.replace("alert-", "postmortem-", 1) in sc.excluded_doc_ids


def test_cascade_scenarios_make_every_listed_affected_service_symptomatic(s_scenarios, s_documents):
    for doc in s_documents:
        if doc.doc_type == "alert" and doc.metadata.get("adversarial_case") == "cascading_failure":
            sc = s_scenarios[doc.doc_id]
            for service in doc.metadata["affected_services"]:
                assert service in sc.symptomatic, (doc.doc_id, service)


# -------------------------------------------------------------- deploy ground truth


def test_a_deploy_can_only_be_the_cause_for_categories_a_deploy_could_cause(s_scenarios):
    plausible = ALWAYS_DEPLOY_CAUSED | SOMETIMES_DEPLOY_CAUSED
    causal = [s for s in s_scenarios.values() if s.deploy_causal]

    assert causal and all(s.category in plausible for s in causal)
    for category in ("disk_full", "certificate_expiry", "third_party_outage", "quality_degradation"):
        assert not any(s.deploy_causal for s in s_scenarios.values() if s.category == category)


def test_the_deploy_mix_makes_blaming_the_deploy_neither_always_right_nor_always_wrong(s_scenarios):
    scenarios = list(s_scenarios.values())
    causal = sum(s.deploy_causal for s in scenarios)
    decoys = sum(s.decoy_deploy for s in scenarios)
    no_deploy_near_onset = sum(not s.deploy_causal and not s.decoy_deploy for s in scenarios)

    assert 0.1 * len(scenarios) < causal < 0.5 * len(scenarios)
    assert decoys >= 0.2 * len(scenarios)  # coincidence is common
    assert no_deploy_near_onset >= 0.2 * len(scenarios)


def test_a_causal_scenario_is_never_also_a_decoy(s_scenarios):
    assert not any(s.deploy_causal and s.decoy_deploy for s in s_scenarios.values())


# -------------------------------------------------------------- metric model


def test_metric_availability_is_derived_from_the_catalog(s_catalog):
    assert available_metrics(s_catalog, "stripe-gateway") == ["request_rate_rps", "error_rate", "latency_p99_ms"]
    assert "disk_used_percent" in available_metrics(s_catalog, "postgres-primary")
    assert "disk_used_percent" not in available_metrics(s_catalog, "redis-cache")  # in-memory
    assert "connection_pool_in_use_percent" in available_metrics(s_catalog, "checkout-api")  # depends on postgres
    assert "queue_depth" in available_metrics(s_catalog, "notification-service")  # depends on kafka
    assert "queue_depth" not in available_metrics(s_catalog, "checkout-api")


def test_every_service_has_at_least_the_universal_or_external_metrics(s_catalog):
    for service in s_catalog:
        assert {"error_rate", "latency_p99_ms", "request_rate_rps"} <= set(available_metrics(s_catalog, service))


def test_a_healthy_service_burns_only_a_fraction_of_its_error_budget(s_catalog):
    telemetry = Telemetry(s_catalog)
    for service, entry in s_catalog.items():
        ratio = telemetry.error_ratio(service, DEFAULT_NOW - timedelta(days=30), DEFAULT_NOW, 721)
        assert 0 < burn_rate(ratio, error_budget_fraction(entry.slo.availability)) < 1.0, service


def test_values_stay_within_their_physical_range(s_catalog, s_scenarios):
    for sc in list(s_scenarios.values())[:30]:
        telemetry = Telemetry(s_catalog, sc)
        for metric in telemetry.available_metrics(sc.root_cause_service):
            for sample in telemetry.series(sc.root_cause_service, metric, sc.now - timedelta(hours=3), sc.now, 40):
                assert sample.value >= 0
                if metric.endswith("_percent"):
                    assert sample.value <= 100
                if metric == "error_rate":
                    assert sample.value <= 1


def test_overlapping_queries_agree_on_shared_instants(s_catalog, s_scenarios):
    sc = next(iter(s_scenarios.values()))
    telemetry = Telemetry(s_catalog, sc)
    t = sc.now.replace(second=0, microsecond=0)

    a = telemetry.value_at(sc.root_cause_service, "latency_p99_ms", t)
    b = telemetry.series(sc.root_cause_service, "latency_p99_ms", t - timedelta(hours=2), t, 3)[-1]

    assert a == b


def test_the_same_service_gets_different_noise_in_different_incidents(s_catalog, s_scenarios):
    first, second = list(s_scenarios.values())[:2]
    t = DEFAULT_NOW

    a = Telemetry(s_catalog, first).value_at("checkout-api", "cpu_percent", t).value
    b = Telemetry(s_catalog, second).value_at("checkout-api", "cpu_percent", t).value

    assert a != b


# -------------------------------------------------------- effects: the signatures


def test_effect_progress_ramps_linearly_and_can_start_before_onset():
    ramp = Effect("memory_percent", "to", 99.0, start_min=-120, ramp_min=120)

    assert ramp.progress(-130) == 0.0
    assert ramp.progress(-60) == pytest.approx(0.5)
    assert ramp.progress(0) == 1.0 and ramp.progress(50) == 1.0


def test_effect_kinds_apply_as_documented():
    assert Effect("error_rate", "add", 0.05).apply(0.01, 1.0) == pytest.approx(0.06)
    assert Effect("latency_p99_ms", "mult", 4.0).apply(100.0, 1.0) == pytest.approx(400.0)
    assert Effect("memory_percent", "to", 100.0).apply(40.0, 1.0) == pytest.approx(100.0)
    assert Effect("latency_p99_ms", "mult", 4.0).apply(100.0, 1.0, amplitude=0.5) == pytest.approx(250.0)
    with pytest.raises(ValueError):
        Effect("x", "sideways", 1.0).apply(1.0, 1.0)


def _scenario_with(find_scenario, category):
    return find_scenario(category=category)


@pytest.mark.parametrize(
    "category, metric, quiet_minutes_before",
    [
        ("connection_pool_exhaustion", "latency_p99_ms", 30),
        ("disk_full", "error_rate", 30),
        ("third_party_outage", "error_rate", 30),
        ("certificate_expiry", "error_rate", 30),
        ("rate_limit_exhaustion", "error_rate", 30),
        ("memory_leak", "memory_percent", 150),  # the leak is already climbing for 2h before onset
    ],
)
def test_a_failure_category_moves_its_signature_metric_at_the_root_service(
    find_scenario, s_catalog, category, metric, quiet_minutes_before
):
    sc = find_scenario(lambda s: metric in available_metrics(s_catalog, s.root_cause_service), category=category)
    telemetry = Telemetry(s_catalog, sc)
    before = telemetry.value_at(sc.root_cause_service, metric, sc.onset - timedelta(minutes=quiet_minutes_before))
    after = telemetry.value_at(sc.root_cause_service, metric, sc.onset + timedelta(minutes=25))

    assert after.value > before.value * 1.5


def test_a_full_disk_climbs_for_hours_before_the_incident_starts(find_scenario, s_catalog):
    sc = find_scenario(lambda s: "disk_used_percent" in available_metrics(s_catalog, s.root_cause_service),
                       category="disk_full")
    telemetry = Telemetry(s_catalog, sc)

    hours_before = telemetry.value_at(sc.root_cause_service, "disk_used_percent", sc.onset - timedelta(hours=3))
    just_before = telemetry.value_at(sc.root_cause_service, "disk_used_percent", sc.onset - timedelta(minutes=5))

    assert just_before.value > hours_before.value + 10
    assert just_before.value > 90


@pytest.mark.parametrize("category", ["quality_degradation", "stale_data"])
def test_failures_that_produce_no_errors_leave_every_metric_untouched(find_scenario, s_catalog, category):
    sc = find_scenario(category=category)
    telemetry = Telemetry(s_catalog, sc)

    for metric in telemetry.available_metrics(sc.root_cause_service):
        tolerance = 4 * METRICS[metric].noise + 0.05  # "untouched" means consistent with that metric's own noise
        for sample in telemetry.series(sc.root_cause_service, metric, sc.onset, sc.now, 12):
            assert abs(sample.value / sample.expected - 1.0) <= tolerance, metric


def test_downstream_services_show_symptoms_later_and_more_weakly_than_the_root(find_scenario, s_catalog):
    sc = find_scenario(lambda s: s.category == "5xx_errors" and any(a < 1.0 for a, _ in s.symptomatic.values()))
    ripple = next(svc for svc, (amplitude, _) in sc.symptomatic.items() if amplitude < 1.0)
    telemetry = Telemetry(s_catalog, sc)
    at = sc.onset + timedelta(minutes=12)

    root = telemetry.value_at(sc.root_cause_service, "error_rate", at)
    downstream = telemetry.value_at(ripple, "error_rate", at)

    assert downstream.value / downstream.expected < root.value / root.expected


def test_the_unrelated_blip_lives_on_a_service_that_is_not_part_of_the_incident(s_scenarios):
    for sc in s_scenarios.values():
        assert sc.blip.service != sc.root_cause_service and sc.blip.service not in sc.symptomatic


def test_the_blip_is_visible_in_the_raw_series(find_scenario, s_catalog):
    sc = find_scenario()
    telemetry = Telemetry(s_catalog, sc)
    during = sc.blip.start + timedelta(minutes=1)
    outside = sc.blip.start - timedelta(minutes=10)

    elevated = telemetry.value_at(sc.blip.service, sc.blip.metric, during)
    normal = telemetry.value_at(sc.blip.service, sc.blip.metric, outside)

    assert elevated.value / elevated.expected > 1.4 > normal.value / normal.expected


def test_no_scenario_means_a_perfectly_ordinary_platform(s_catalog):
    telemetry = Telemetry(s_catalog)

    assert telemetry.now == DEFAULT_NOW and telemetry.scenario is None
    for sample in telemetry.series("checkout-api", "error_rate", DEFAULT_NOW - timedelta(hours=2), DEFAULT_NOW, 24):
        assert sample.value / sample.expected < 2.0


def test_deploys_are_deterministic_and_sorted(s_catalog):
    telemetry = Telemetry(s_catalog)

    a = telemetry.deploys("checkout-api", DEFAULT_NOW - timedelta(days=30), DEFAULT_NOW)
    b = telemetry.deploys("checkout-api", DEFAULT_NOW - timedelta(days=30), DEFAULT_NOW)

    assert a == b and a == sorted(a, key=lambda r: r.deployed_at)


def test_deploy_cadence_tracks_service_tier(s_catalog):
    telemetry = Telemetry(s_catalog)
    start = DEFAULT_NOW - timedelta(days=300)
    tier1 = len(telemetry.deploys("checkout-api", start, DEFAULT_NOW))
    tier3 = len(telemetry.deploys("ci-pipeline", start, DEFAULT_NOW))

    assert tier1 > tier3 > 0


def test_third_party_services_have_no_deploys(s_catalog):
    assert Telemetry(s_catalog).deploys("stripe-gateway", DEFAULT_NOW - timedelta(days=60), DEFAULT_NOW) == []


def test_a_causal_scenario_injects_a_deploy_shortly_before_onset(find_scenario, s_catalog):
    sc = find_scenario(deploy_causal=True)
    deploys = Telemetry(s_catalog, sc).deploys(sc.root_cause_service, sc.onset - timedelta(hours=2), sc.now)

    gaps = [(sc.onset - d.deployed_at).total_seconds() / 60 for d in deploys]
    assert any(2 <= gap <= 22 for gap in gaps)


def test_a_decoy_scenario_has_a_deploy_before_onset_but_the_deploy_is_not_the_cause(find_scenario, s_catalog):
    sc = find_scenario(decoy_deploy=True)
    deploys = Telemetry(s_catalog, sc).deploys(sc.root_cause_service, sc.onset - timedelta(hours=2), sc.onset)

    assert not sc.deploy_causal
    assert any(5 <= (sc.onset - d.deployed_at).total_seconds() / 60 <= 60 for d in deploys)


def test_causal_and_decoy_deploy_summaries_come_from_overlapping_pools(s_scenarios, s_catalog):
    """The changelog text must not be a tell: both kinds draw on the same bland
    and risky-sounding summaries."""
    causal_texts, decoy_texts = Counter(), Counter()
    for sc in s_scenarios.values():
        if sc.deploy_causal or sc.decoy_deploy:
            near = [d for d in Telemetry(s_catalog, sc).deploys(sc.root_cause_service, sc.onset - timedelta(hours=2), sc.onset)
                    if (sc.onset - d.deployed_at) <= timedelta(minutes=60)]
            for d in near:
                (causal_texts if sc.deploy_causal else decoy_texts)[d.change_summary] += 1

    assert set(causal_texts) & set(decoy_texts), "no shared summaries: the text would give the answer away"
