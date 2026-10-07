import json
from dataclasses import replace
from datetime import timedelta

import pytest

from meridian.slo import error_budget_fraction
from meridian.tools import Toolset, ToolError

HOUR = timedelta(hours=1)


def call(ctx, **kwargs):
    return Toolset(ctx).functions["compute_error_budget"](**kwargs)


class StubTelemetry:
    """Error ratios chosen by window length, so the burn-tier logic can be
    exercised at exact burn rates the scenarios can't be dialed to."""

    def __init__(self, real, ratio_for_span):
        self._real, self._ratio_for_span = real, ratio_for_span
        self.scenario = real.scenario

    @property
    def now(self):
        return self._real.now

    def error_ratio(self, service, start, end, n_points=96):
        return self._ratio_for_span(end - start)


def stubbed(ctx, ratio_for_span):
    return replace(ctx, telemetry=StubTelemetry(ctx.telemetry, ratio_for_span))


# ----------------------------------------------------------------- healthy case


def test_a_healthy_service_burns_below_budget_and_needs_nothing(s_ctx):
    result = call(s_ctx, service="checkout-api")

    assert result["recommendation"] == "none" and result["highest_breached_tier"] is None
    assert 0 < result["current_burn_rate"] < 1
    assert not any(w["breached"] for w in result["windows"])
    assert result["exhausted"] is False and 0 < result["budget_remaining_fraction"] < 1
    assert "no burn-rate tier is breached" in result["assessment"]
    json.dumps(result)


def test_the_result_has_the_documented_shape(s_ctx):
    result = call(s_ctx, service="checkout-api")

    assert {
        "service", "slo_target_percent", "window_days", "error_budget_fraction", "allowed_downtime_minutes",
        "budget_consumed_fraction", "budget_remaining_fraction", "exhausted", "current_burn_rate",
        "time_to_exhaustion_hours", "windows", "recommendation", "highest_breached_tier", "basis", "assessment",
    } <= set(result)
    assert [w["tier"] for w in result["windows"]] == ["fast", "medium", "slow", "trickle"]
    assert set(result["windows"][0]) == {
        "tier", "long_window", "short_window", "threshold", "long_burn_rate", "short_burn_rate", "breached", "action",
    }


def test_thirty_day_thresholds_come_through_the_tool(s_ctx):
    windows = call(s_ctx, service="checkout-api", window_days=30)["windows"]

    assert [w["threshold"] for w in windows] == pytest.approx([14.4, 6.0, 3.0, 1.0])
    assert [(w["long_window"], w["short_window"]) for w in windows] == [
        ("1h", "5m"), ("6h", "30m"), ("24h", "2h"), ("72h", "6h"),
    ]


def test_twenty_eight_day_thresholds_come_through_the_tool(s_ctx):
    windows = call(s_ctx, service="checkout-api", window_days=28)["windows"]

    assert windows[0]["threshold"] == pytest.approx(13.44)
    assert windows[1]["threshold"] == pytest.approx(5.6)


def test_the_slo_defaults_to_the_catalog_target(s_ctx, s_catalog):
    result = call(s_ctx, service="checkout-api")

    assert result["slo_target_percent"] == s_catalog["checkout-api"].slo.availability == 99.95
    assert result["error_budget_fraction"] == pytest.approx(0.0005)
    assert result["allowed_downtime_minutes"] == pytest.approx(0.0005 * 30 * 24 * 60)  # 21.6 minutes


def test_an_explicit_slo_target_changes_the_budget_and_so_the_burn_rate(s_ctx):
    strict = call(s_ctx, service="checkout-api", slo_target=99.95)
    lax = call(s_ctx, service="checkout-api", slo_target=99.0)

    assert lax["error_budget_fraction"] == pytest.approx(error_budget_fraction(99.0))
    assert strict["current_burn_rate"] == pytest.approx(lax["current_burn_rate"] * 20, rel=0.02)


def test_third_party_services_are_budgeted_against_their_vendor_target(s_ctx, s_catalog):
    result = call(s_ctx, service="stripe-gateway")

    assert result["slo_target_percent"] == s_catalog["stripe-gateway"].slo.availability


def test_the_canonical_name_is_reported_for_a_differently_cased_input(s_ctx):
    assert call(s_ctx, service="Checkout-API")["service"] == "checkout-api"


# ----------------------------------------------------------------- real incidents


def test_a_total_outage_pages(find_scenario, ctx_for):
    sc = find_scenario(category="certificate_expiry")  # 95% of requests fail

    result = call(ctx_for(sc.incident_id), service=sc.root_cause_service)

    assert result["recommendation"] == "page" and result["highest_breached_tier"] == "fast"
    assert result["windows"][0]["breached"] and result["windows"][0]["action"] == "page"
    assert result["current_burn_rate"] > 14.4
    assert "page" in result["assessment"]


def test_a_subtle_failure_with_no_errors_shows_no_burn(find_scenario, ctx_for):
    sc = find_scenario(category="quality_degradation")

    result = call(ctx_for(sc.incident_id), service=sc.root_cause_service)

    assert result["recommendation"] == "none" and result["current_burn_rate"] < 1


# -------------------------------------------------------- multi-window logic


def test_both_the_long_and_short_window_must_burn_for_a_tier_to_breach(s_ctx):
    budget = 0.0005
    hot_long_cold_short = stubbed(
        s_ctx, lambda span: 20 * budget if span >= HOUR else 0.1 * budget  # an old problem that has since been fixed
    )

    result = call(hot_long_cold_short, service="checkout-api")

    fast = result["windows"][0]
    assert fast["long_burn_rate"] > fast["threshold"] > fast["short_burn_rate"]
    assert fast["breached"] is False


def test_a_tier_breaches_when_both_windows_exceed_its_threshold(s_ctx):
    budget = 0.0005
    result = call(stubbed(s_ctx, lambda span: 20 * budget), service="checkout-api")

    assert all(w["breached"] for w in result["windows"][:2]) and result["recommendation"] == "page"


def test_only_ticket_tiers_breaching_recommends_a_ticket_not_a_page(s_ctx):
    budget = 0.0005

    def ratio(span):
        # hot for exactly the slow tier's windows (24h long, 2h short), cool elsewhere
        return 3.5 * budget if span in (timedelta(hours=24), timedelta(hours=2)) else 0.5 * budget

    result = call(stubbed(s_ctx, ratio), service="checkout-api")

    breached = [w["tier"] for w in result["windows"] if w["breached"]]
    assert breached == ["slow"] and result["recommendation"] == "ticket"
    assert result["highest_breached_tier"] == "slow"


def test_a_burn_just_under_the_threshold_does_not_breach(s_ctx):
    budget = 0.0005
    result = call(stubbed(s_ctx, lambda span: 14.3 * budget), service="checkout-api")

    assert result["windows"][0]["breached"] is False


def test_a_blown_budget_is_reported_as_exhausted(s_ctx):
    budget = 0.0005
    result = call(stubbed(s_ctx, lambda span: 2.0 * budget), service="checkout-api")

    assert result["exhausted"] is True and result["budget_remaining_fraction"] < 0
    assert result["time_to_exhaustion_hours"] == 0.0
    assert "already exhausted" in result["assessment"]


def test_time_to_exhaustion_follows_the_current_burn_rate(s_ctx):
    budget = 0.0005
    result = call(stubbed(s_ctx, lambda span: 1.0 * budget), service="checkout-api")

    assert result["current_burn_rate"] == pytest.approx(1.0)
    assert result["budget_consumed_fraction"] == pytest.approx(1.0)  # exactly on plan: used it all by the end
    assert result["time_to_exhaustion_hours"] == 0.0

    half = call(stubbed(s_ctx, lambda span: 0.5 * budget), service="checkout-api")
    assert half["budget_remaining_fraction"] == pytest.approx(0.5)
    assert half["time_to_exhaustion_hours"] == pytest.approx(0.5 * 720 / 0.5, rel=1e-3)


def test_nothing_burning_means_no_exhaustion_time(s_ctx):
    result = call(stubbed(s_ctx, lambda span: 0.0), service="checkout-api")

    assert result["time_to_exhaustion_hours"] is None and result["current_burn_rate"] == 0


# ------------------------------------------------------------------ validation


@pytest.mark.parametrize("slo_target", [0.999, 1.0, 100, 150, -5])
def test_slo_target_must_be_a_percentage_not_a_fraction(s_ctx, slo_target):
    with pytest.raises(ToolError, match="slo_target"):
        call(s_ctx, service="checkout-api", slo_target=slo_target)


@pytest.mark.parametrize("window_days", [0, 6, 91, 365])
def test_window_days_is_bounded(s_ctx, window_days):
    with pytest.raises(ToolError, match="window_days"):
        call(s_ctx, service="checkout-api", window_days=window_days)


def test_unknown_service_suggests_near_matches(s_ctx):
    with pytest.raises(ToolError, match="Did you mean: checkout-api"):
        call(s_ctx, service="checkout-ap")
