"""Error-budget math for multi-window, multi-burn-rate alerting.

Vocabulary:
- error budget fraction: how much unreliability the SLO allows, 1 - SLO
  (99.95% -> 0.0005).
- burn rate: how fast the budget is being spent relative to plan. 1.0 means
  "exactly exhausted at the end of the SLO window"; 14.4 means 14.4x too fast.
  burn rate = observed error ratio / error budget fraction.

Alert thresholds are not magic numbers. Each tier is defined by *what it is
meant to catch*: "spending `budget_consumed` of the whole budget within
`long_window`". Sustaining burn rate B for a window of W hours consumes
B * W / (SLO window hours) of the budget, so

    threshold B = budget_consumed * slo_window_hours / long_window_hours

which for a 30-day SLO gives 14.4 / 6 / 3 / 1 and for a 28-day SLO gives
13.44 / 5.6 / 2.8 / 0.933 -- derived, so they stay right for any window.

Each tier also has a short window (1/12 of the long one) that must be burning
too: the long window alone keeps alerting for an hour after the problem is
fixed; requiring the short window to still be hot makes the alert reset
quickly. This is the multi-window formulation from Google's SRE Workbook,
which is what produces the 14.4/6/3/1 figures.
"""

from __future__ import annotations

from dataclasses import dataclass

SHORT_WINDOW_DIVISOR = 12


@dataclass(frozen=True)
class BurnTier:
    name: str
    budget_consumed: float  # fraction of the whole budget this tier should catch burning
    long_window_hours: float
    action: str  # "page" wakes someone; "ticket" can wait for working hours

    @property
    def short_window_hours(self) -> float:
        return self.long_window_hours / SHORT_WINDOW_DIVISOR

    def threshold(self, slo_window_days: float) -> float:
        return self.budget_consumed * (slo_window_days * 24.0) / self.long_window_hours


TIERS: tuple[BurnTier, ...] = (
    BurnTier("fast", budget_consumed=0.02, long_window_hours=1, action="page"),
    BurnTier("medium", budget_consumed=0.05, long_window_hours=6, action="page"),
    BurnTier("slow", budget_consumed=0.10, long_window_hours=24, action="ticket"),
    BurnTier("trickle", budget_consumed=0.10, long_window_hours=72, action="ticket"),
)


def burn_thresholds(slo_window_days: float) -> list[tuple[BurnTier, float]]:
    return [(tier, round(tier.threshold(slo_window_days), 6)) for tier in TIERS]


def error_budget_fraction(slo_percent: float) -> float:
    if not 0.0 < slo_percent < 100.0:
        raise ValueError(f"SLO must be a percentage strictly between 0 and 100, got {slo_percent}")
    return 1.0 - slo_percent / 100.0


def burn_rate(error_ratio: float, budget_fraction: float) -> float:
    return error_ratio / budget_fraction


def budget_consumed(window_error_ratio: float, budget_fraction: float) -> float:
    """Share of the SLO window's budget spent, given the error ratio over the
    window so far. Above 1.0 means the budget is blown."""
    return window_error_ratio / budget_fraction


def hours_to_exhaustion(remaining_fraction: float, current_burn_rate: float, slo_window_days: float) -> float | None:
    """How long until the budget is gone if the current burn rate holds.
    0 when already exhausted; None when nothing is burning."""
    if remaining_fraction <= 0:
        return 0.0
    if current_burn_rate <= 0:
        return None
    return remaining_fraction * (slo_window_days * 24.0) / current_burn_rate
