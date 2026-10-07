import json
from datetime import datetime, timedelta, timezone

import pytest

from meridian.telemetry import DEFAULT_NOW, Sample, Telemetry
from meridian.tools import Toolset, ToolError
from meridian.tools.telemetry_tools import _detect_anomaly, parse_window

UTC = timezone.utc
T0 = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def call(ctx, name, /, **kwargs):
    return Toolset(ctx).functions[name](**kwargs)


# --------------------------------------------------------- anomaly detector


def samples_with(ratios, step_minutes=1.0):
    return [Sample(T0 + timedelta(minutes=i * step_minutes), r * 10.0, 10.0) for i, r in enumerate(ratios)]


def test_a_deviation_that_already_ended_must_have_lasted_five_minutes():
    blip = samples_with([1, 1, 2.5, 2.5, 2.5, 1, 1, 1, 1, 1])  # 3 samples = 3 min, then back to normal

    assert _detect_anomaly(blip, 1.0)["detected"] is False


def test_a_sustained_deviation_that_ended_is_detected_with_its_start():
    run = samples_with([1, 1, 3, 3, 3, 3, 3, 3, 1, 1])

    result = _detect_anomaly(run, 1.0)

    assert result["detected"] and result["ongoing"] is False
    assert result["started_at"] == iso(T0 + timedelta(minutes=2))
    assert result["direction"] == "above" and result["peak_ratio_vs_expected"] == 3.0


def test_a_deviation_still_in_progress_counts_after_two_minutes():
    fresh = samples_with([1, 1, 1, 1, 1, 1, 1, 4, 4, 4])  # 3 min and still going

    result = _detect_anomaly(fresh, 1.0)

    assert result["detected"] and result["ongoing"] is True


def test_a_deviation_that_just_began_is_not_yet_reported():
    assert _detect_anomaly(samples_with([1, 1, 1, 1, 1, 1, 1, 1, 4]), 1.0)["detected"] is False


def test_a_drop_is_detected_as_below_expected():
    result = _detect_anomaly(samples_with([1, 1, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 1]), 1.0)

    assert result["detected"] and result["direction"] == "below"


def test_the_first_sustained_run_is_the_one_reported():
    result = _detect_anomaly(samples_with([1, 3, 3, 3, 3, 3, 3, 1, 1, 5, 5, 5, 5, 5, 5, 1]), 1.0)

    assert result["started_at"] == iso(T0 + timedelta(minutes=1))


def test_a_quiet_series_says_quiet_is_not_proof_of_health():
    result = _detect_anomaly(samples_with([1.0] * 20), 1.0)

    assert result["detected"] is False and "does not prove" in result["note"]


def test_deviations_inside_the_normal_band_are_ignored():
    assert _detect_anomaly(samples_with([1.4, 0.6] * 10), 1.0)["detected"] is False


# --------------------------------------------------------------- parse_window


@pytest.mark.parametrize("text, expected", [("5m", 5), ("90m", 90), ("1h", 60), ("24h", 1440), ("7d", 10080)])
def test_parse_window_units(text, expected):
    span = parse_window(text, minimum=timedelta(minutes=5), maximum=timedelta(days=7), label="x")

    assert span == timedelta(minutes=expected)


@pytest.mark.parametrize("text", ["2w", "abc", "1.5h", "", "h", "-5m"])
def test_parse_window_rejects_malformed_text(text):
    with pytest.raises(ToolError, match="not valid"):
        parse_window(text, minimum=timedelta(minutes=5), maximum=timedelta(days=7), label="x")


@pytest.mark.parametrize("text", ["4m", "8d"])
def test_parse_window_rejects_out_of_range_spans_and_says_the_range(text):
    with pytest.raises(ToolError, match="between 5m and 7d"):
        parse_window(text, minimum=timedelta(minutes=5), maximum=timedelta(days=7), label="x")


# --------------------------------------------------------------- query_metrics


def test_query_metrics_result_shape(s_ctx):
    result = call(s_ctx, "query_metrics", service="checkout-api", metric="latency_p99_ms", window="1h")

    assert {"service", "metric", "unit", "window", "start", "end", "points", "summary", "anomaly"} <= set(result)
    assert result["unit"] == "ms" and len(result["points"]) == 24
    assert set(result["points"][0]) == {"t", "value", "expected"}
    assert {"latest", "mean", "min", "max", "peak_at", "expected_mean", "latest_vs_expected"} <= set(result["summary"])
    json.dumps(result)


def test_the_window_ends_now_and_spans_the_requested_length(s_ctx):
    result = call(s_ctx, "query_metrics", service="checkout-api", metric="error_rate", window="6h")

    assert parse(result["end"]) == s_ctx.now == DEFAULT_NOW
    assert parse(result["end"]) - parse(result["start"]) == timedelta(hours=6)
    assert parse(result["points"][-1]["t"]) == s_ctx.now


def test_points_are_in_time_order(s_ctx):
    points = call(s_ctx, "query_metrics", service="checkout-api", metric="error_rate", window="24h")["points"]

    times = [parse(p["t"]) for p in points]
    assert times == sorted(times)


def test_a_healthy_platform_shows_no_anomaly_anywhere(s_ctx, s_catalog):
    for service in ("checkout-api", "postgres-primary", "llm-gateway", "stripe-gateway"):
        for metric in Telemetry(s_catalog).available_metrics(service):
            result = call(s_ctx, "query_metrics", service=service, metric=metric, window="1h")
            assert result["anomaly"]["detected"] is False, (service, metric)


def test_a_connection_pool_incident_shows_up_on_the_pool_and_latency_with_a_plausible_start(find_scenario, ctx_for, s_catalog):
    sc = find_scenario(lambda s: "connection_pool_in_use_percent" in Telemetry(s_catalog).available_metrics(s.root_cause_service),
                       category="connection_pool_exhaustion")
    ctx = ctx_for(sc.incident_id)

    pool = call(ctx, "query_metrics", service=sc.root_cause_service, metric="connection_pool_in_use_percent")
    latency = call(ctx, "query_metrics", service=sc.root_cause_service, metric="latency_p99_ms")

    for result in (pool, latency):
        assert result["anomaly"]["detected"] and result["anomaly"]["direction"] == "above"
        assert sc.onset - timedelta(minutes=1) <= parse(result["anomaly"]["started_at"]) <= sc.now
    assert pool["summary"]["latest_vs_expected"] > 1.5


def test_the_onset_is_far_earlier_than_the_alert_so_it_has_to_be_read_from_the_metrics(find_scenario, ctx_for):
    sc = find_scenario(category="third_party_outage")
    result = call(ctx_for(sc.incident_id), "query_metrics", service=sc.root_cause_service, metric="error_rate")

    assert parse(result["anomaly"]["started_at"]) < sc.now - timedelta(minutes=2)


def test_a_fresh_incident_is_reported_as_ongoing(find_scenario, ctx_for):
    sc = find_scenario(category="third_party_outage")

    anomaly = call(ctx_for(sc.incident_id), "query_metrics", service=sc.root_cause_service, metric="error_rate")["anomaly"]

    assert anomaly["ongoing"] is True


@pytest.mark.parametrize("category", ["quality_degradation", "stale_data"])
def test_silent_failures_report_no_anomaly_and_say_that_does_not_mean_fine(find_scenario, ctx_for, s_catalog, category):
    sc = find_scenario(category=category)
    ctx = ctx_for(sc.incident_id)

    for metric in Telemetry(s_catalog).available_metrics(sc.root_cause_service):
        anomaly = call(ctx, "query_metrics", service=sc.root_cause_service, metric=metric)["anomaly"]
        assert anomaly["detected"] is False
    assert "does not prove" in anomaly["note"]


def test_the_unrelated_blip_is_visible_in_the_data_but_not_flagged_as_the_incident(find_scenario, ctx_for):
    sc = find_scenario()
    ctx = ctx_for(sc.incident_id)

    result = call(ctx, "query_metrics", service=sc.blip.service, metric=sc.blip.metric, window="1h")

    assert result["summary"]["max"] > 1.4 * result["summary"]["expected_mean"] * 0.9
    assert result["anomaly"]["detected"] is False


def test_a_downstream_service_shows_symptoms_too(find_scenario, ctx_for):
    sc = find_scenario(lambda s: s.category == "5xx_errors" and any(a == 1.0 for a, _ in s.symptomatic.values()))
    downstream = next(svc for svc, (amplitude, _) in sc.symptomatic.items() if amplitude == 1.0)

    result = call(ctx_for(sc.incident_id), "query_metrics", service=downstream, metric="error_rate")

    assert result["anomaly"]["detected"]


def test_a_seven_day_window_works(s_ctx):
    result = call(s_ctx, "query_metrics", service="checkout-api", metric="request_rate_rps", window="7d")

    assert len(result["points"]) == 24 and parse(result["end"]) - parse(result["start"]) == timedelta(days=7)


def test_query_metrics_is_case_insensitive_and_reports_the_canonical_name(s_ctx):
    assert call(s_ctx, "query_metrics", service="Checkout-API", metric="error_rate")["service"] == "checkout-api"
    assert call(s_ctx, "get_deploy_history", service="CHECKOUT-API")["service"] == "checkout-api"


def test_query_metrics_unknown_service_suggests_near_matches(s_ctx):
    with pytest.raises(ToolError, match="Did you mean: checkout-api"):
        call(s_ctx, "query_metrics", service="checkout-ap", metric="error_rate")


def test_asking_for_a_metric_a_service_lacks_lists_the_ones_it_has(s_ctx):
    with pytest.raises(ToolError) as exc:
        call(s_ctx, "query_metrics", service="checkout-api", metric="disk_used_percent")

    assert "no 'disk_used_percent' metric" in str(exc.value) and "error_rate" in str(exc.value)


def test_third_party_services_only_expose_the_metrics_observed_from_our_side(s_ctx):
    with pytest.raises(ToolError, match="Available for this service: request_rate_rps, error_rate, latency_p99_ms"):
        call(s_ctx, "query_metrics", service="stripe-gateway", metric="cpu_percent")


@pytest.mark.parametrize("window", ["2w", "4m", "8d", "soon"])
def test_query_metrics_rejects_bad_windows(s_ctx, window):
    with pytest.raises(ToolError):
        call(s_ctx, "query_metrics", service="checkout-api", metric="error_rate", window=window)


def test_query_metrics_rejects_an_unknown_metric_name_listing_the_choices(s_ctx):
    with pytest.raises(ToolError, match="error_rate"):
        call(s_ctx, "query_metrics", service="checkout-api", metric="vibes")


def test_query_metrics_is_deterministic(find_scenario, ctx_for):
    sc = find_scenario()
    ctx = ctx_for(sc.incident_id)

    a = call(ctx, "query_metrics", service=sc.root_cause_service, metric="error_rate")
    b = call(ctx, "query_metrics", service=sc.root_cause_service, metric="error_rate")

    assert a == b


# ----------------------------------------------------------- get_deploy_history


def test_deploy_history_result_shape(s_ctx):
    result = call(s_ctx, "get_deploy_history", service="checkout-api", window="30d")

    assert {"service", "window", "start", "end", "count", "deploys"} <= set(result)
    assert result["count"] == len(result["deploys"]) > 0
    assert set(result["deploys"][0]) == {
        "deploy_id", "deployed_at", "minutes_before_now", "version", "deployed_by",
        "change_type", "change_summary", "status",
    }
    json.dumps(result)


def test_deploys_are_newest_first_and_inside_the_window(s_ctx):
    result = call(s_ctx, "get_deploy_history", service="checkout-api", window="30d")
    times = [parse(d["deployed_at"]) for d in result["deploys"]]

    assert times == sorted(times, reverse=True)
    assert all(parse(result["start"]) <= t <= parse(result["end"]) for t in times)


def test_minutes_before_now_matches_the_timestamps(s_ctx):
    for d in call(s_ctx, "get_deploy_history", service="checkout-api", window="14d")["deploys"]:
        assert d["minutes_before_now"] == round((s_ctx.now - parse(d["deployed_at"])).total_seconds() / 60)


def test_a_narrower_window_returns_a_subset(s_ctx):
    wide = {d["deploy_id"] for d in call(s_ctx, "get_deploy_history", service="checkout-api", window="30d")["deploys"]}
    narrow = {d["deploy_id"] for d in call(s_ctx, "get_deploy_history", service="checkout-api", window="7d")["deploys"]}

    assert narrow < wide


def test_third_party_services_have_no_deploys_and_say_why(s_ctx):
    result = call(s_ctx, "get_deploy_history", service="stripe-gateway", window="30d")

    assert result["deploys"] == [] and "Third-party" in result["note"]


def test_a_causal_deploy_lands_shortly_before_the_metric_starts_moving(find_scenario, ctx_for):
    sc = find_scenario(lambda s: s.deploy_causal and s.category == "5xx_errors")
    ctx = ctx_for(sc.incident_id)

    deploys = call(ctx, "get_deploy_history", service=sc.root_cause_service, window="6h")["deploys"]
    onset = parse(call(ctx, "query_metrics", service=sc.root_cause_service, metric="error_rate")["anomaly"]["started_at"])

    recent = [d for d in deploys if 0 < (onset - parse(d["deployed_at"])).total_seconds() / 60 <= 25]
    assert recent, "an agent comparing deploy time with the metric onset should be able to see the link"


def test_a_coincidental_deploy_is_indistinguishable_by_text_but_not_by_the_failure_pattern(find_scenario, ctx_for):
    sc = find_scenario(lambda s: s.decoy_deploy and s.category in {"disk_full", "third_party_outage", "certificate_expiry"})
    ctx = ctx_for(sc.incident_id)

    deploys = call(ctx, "get_deploy_history", service=sc.root_cause_service, window="2h")["deploys"]

    assert deploys  # a deploy really did land shortly before: the lure exists
    assert sc.category in {"disk_full", "third_party_outage", "certificate_expiry"}  # ...but a deploy cannot cause these


def test_a_deploy_does_not_always_precede_an_incident(s_scenarios, ctx_for):
    near = 0
    for sc in s_scenarios.values():
        ctx = ctx_for(sc.incident_id)
        deploys = ctx.telemetry.deploys(sc.root_cause_service, sc.onset - timedelta(minutes=60), sc.onset)
        near += bool(deploys)
    share = near / len(s_scenarios)

    assert 0.25 < share < 0.85


def test_deploy_history_validates_its_inputs(s_ctx):
    with pytest.raises(ToolError, match="between 5m and 30d"):
        call(s_ctx, "get_deploy_history", service="checkout-api", window="60d")
    with pytest.raises(ToolError, match="Did you mean"):
        call(s_ctx, "get_deploy_history", service="checkout-monolith", window="24h")


def test_deploy_history_is_deterministic(s_ctx):
    assert call(s_ctx, "get_deploy_history", service="orders-service", window="14d") == call(
        s_ctx, "get_deploy_history", service="orders-service", window="14d"
    )
