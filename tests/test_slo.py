"""Error-budget math. The headline assertions: a 30-day SLO window yields burn
thresholds of 14.4 / 6 / 3 / 1 and a 28-day window yields 13.44 -- both
*derived* from what each tier is meant to catch, never stored."""

import pytest

from meridian.slo import (
    TIERS,
    BurnTier,
    budget_consumed,
    burn_rate,
    burn_thresholds,
    error_budget_fraction,
    hours_to_exhaustion,
)


def thresholds(days):
    return {tier.name: value for tier, value in burn_thresholds(days)}


def test_a_30_day_window_yields_14_4_6_3_and_1():
    values = thresholds(30)

    assert values["fast"] == pytest.approx(14.4)
    assert values["medium"] == pytest.approx(6.0)
    assert values["slow"] == pytest.approx(3.0)
    assert values["trickle"] == pytest.approx(1.0)
    assert [v for _, v in burn_thresholds(30)] == pytest.approx([14.4, 6, 3, 1])


def test_a_28_day_window_yields_13_44():
    values = thresholds(28)

    assert values["fast"] == pytest.approx(13.44)
    assert values["medium"] == pytest.approx(5.6)
    assert values["slow"] == pytest.approx(2.8)
    assert values["trickle"] == pytest.approx(0.933333, rel=1e-5)


def test_thresholds_are_derived_so_they_scale_with_the_window():
    assert thresholds(60)["fast"] == pytest.approx(2 * thresholds(30)["fast"])
    assert thresholds(7)["fast"] == pytest.approx(3.36)
    assert thresholds(90)["trickle"] == pytest.approx(3.0)


@pytest.mark.parametrize("days", [7, 14, 28, 30, 45, 90])
def test_each_threshold_really_catches_the_budget_share_its_tier_promises(days):
    """Burn B sustained for a tier's long window consumes B * W / (SLO window)
    of the budget; that must come out to exactly the share the tier targets."""
    for tier, threshold in burn_thresholds(days):
        consumed = threshold * tier.long_window_hours / (days * 24)
        assert consumed == pytest.approx(tier.budget_consumed, rel=1e-5), tier.name


def test_the_14_4_figure_means_two_percent_of_a_30_day_budget_in_one_hour():
    assert 14.4 * 1 / (30 * 24) == pytest.approx(0.02)


def test_short_windows_are_a_twelfth_of_the_long_ones():
    shorts = {tier.name: tier.short_window_hours for tier in TIERS}

    assert shorts == {"fast": pytest.approx(5 / 60), "medium": pytest.approx(0.5), "slow": 2.0, "trickle": 6.0}


def test_fast_and_medium_page_while_slow_and_trickle_only_ticket():
    assert {tier.name: tier.action for tier in TIERS} == {
        "fast": "page", "medium": "page", "slow": "ticket", "trickle": "ticket",
    }


def test_thresholds_follow_the_tier_definition_rather_than_being_stored():
    """Change what a tier is meant to catch and its threshold changes with it:
    4% of the budget in 2 hours over a 30-day window is 4% * 720 / 2 = 14.4,
    reached by a different route than the standard fast tier."""
    custom = BurnTier("custom", budget_consumed=0.04, long_window_hours=2, action="page")

    assert custom.threshold(30) == pytest.approx(14.4)
    assert custom.threshold(28) == pytest.approx(13.44)
    assert BurnTier("custom", budget_consumed=0.01, long_window_hours=2, action="page").threshold(30) == pytest.approx(3.6)


@pytest.mark.parametrize("slo_percent, budget", [(99.95, 0.0005), (99.9, 0.001), (99.0, 0.01), (99.99, 0.0001)])
def test_error_budget_fraction(slo_percent, budget):
    assert error_budget_fraction(slo_percent) == pytest.approx(budget)


@pytest.mark.parametrize("bad", [0, 100, -1, 100.5])
def test_error_budget_fraction_rejects_percentages_outside_the_open_range(bad):
    with pytest.raises(ValueError):
        error_budget_fraction(bad)


def test_burn_rate_is_error_ratio_over_budget():
    assert burn_rate(0.0005, 0.0005) == pytest.approx(1.0)  # exactly on plan
    assert burn_rate(0.0072, 0.0005) == pytest.approx(14.4)
    assert burn_rate(0.0002, 0.0005) == pytest.approx(0.4)  # the "0.4x does not justify a page" case
    assert burn_rate(0.0, 0.0005) == 0.0


def test_budget_consumed_above_one_means_the_budget_is_blown():
    assert budget_consumed(0.0005, 0.0005) == pytest.approx(1.0)
    assert budget_consumed(0.001, 0.0005) == pytest.approx(2.0)


def test_hours_to_exhaustion():
    assert hours_to_exhaustion(0.5, 2.0, 30) == pytest.approx(180.0)  # half left, burning at 2x
    assert hours_to_exhaustion(1.0, 1.0, 30) == pytest.approx(720.0)  # a full window at exactly 1x
    assert hours_to_exhaustion(0.0, 5.0, 30) == 0.0 and hours_to_exhaustion(-0.2, 5.0, 30) == 0.0
    assert hours_to_exhaustion(0.5, 0.0, 30) is None  # nothing burning
