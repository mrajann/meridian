"""compute_error_budget: multi-window burn-rate analysis for one service."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated, Any

from pydantic import Field

from meridian import slo
from meridian.tools.catalog_tools import require_service
from meridian.tools.context import ToolContext
from meridian.tools.registry import tool
from meridian.tools.types import ServiceName

_SAMPLES_PER_WINDOW = 120


def _hours_label(hours: float) -> str:
    return f"{round(hours * 60)}m" if hours < 1 else f"{hours:g}h"


@tool
def compute_error_budget(
    ctx: ToolContext,
    service: ServiceName,
    slo_target: Annotated[float, Field(gt=1, lt=100)] | None = None,
    window_days: Annotated[int, Field(ge=7, le=90)] = 30,
) -> dict:
    """Work out how fast a service is burning its error budget and whether that justifies waking someone.

    Use this when deciding how urgently to escalate. The error budget is the unreliability the SLO allows
    (99.95% allows 0.05%); the burn rate is how fast it is being spent relative to plan: 1.0 means the budget
    runs out exactly at the end of the SLO window, 14.4 means 14.4 times too fast (2% of a 30-day budget gone in
    one hour). A burn rate of 14x justifies a 3am page; 0.4x does not.

    Four alert tiers are evaluated, each pairing a long window with a short one that must also be burning (so an
    alert stops firing soon after a fix): fast (1h/5m) and medium (6h/30m) are page-worthy; slow (24h/2h) and
    trickle (72h/6h) are ticket-worthy. The thresholds are derived from the SLO window, not fixed -- for a
    30-day window they are 14.4, 6, 3 and 1, for 28 days 13.44, 5.6, 2.8 and 0.933. `recommendation` is "page"
    if a page tier is breached, "ticket" if only a ticket tier is, otherwise "none".

    The recommendation is one input, not the decision: weigh it against the service's tier and
    business_hours_only (get_service), customer impact, and whether the incident is still getting worse. Burn is
    computed from the service's error rate, so an incident that does not produce errors (degraded output quality,
    stale data) will show no burn here even though customers are affected; do not read "none" as "fine".

    Do not use this to find out what is failing or why (use query_metrics and the dependency tools): it measures
    how much reliability budget is being spent, not the cause.

    Args:
        service: Service name, e.g. "checkout-api".
        slo_target: Availability SLO as a percentage, e.g. 99.9 for 99.9% (not 0.999). Omit to use the
            service's own target from the catalog.
        window_days: The SLO's rolling window in days, 7 to 90. Default 30.

    Returns:
        error_budget_fraction, allowed_downtime_minutes, budget_consumed_fraction, budget_remaining_fraction,
        exhausted, current_burn_rate (1h), time_to_exhaustion_hours, windows (per tier: long/short window, derived
        threshold, burn rates, breached, action), recommendation, highest_breached_tier, and a plain-language
        assessment.
    """
    entry = require_service(ctx, service)
    target = entry.slo.availability if slo_target is None else slo_target
    budget = slo.error_budget_fraction(target)
    now, telemetry = ctx.now, ctx.telemetry

    windows: list[dict[str, Any]] = []
    for tier, threshold in slo.burn_thresholds(window_days):
        long_burn = slo.burn_rate(
            telemetry.error_ratio(service, now - timedelta(hours=tier.long_window_hours), now, _SAMPLES_PER_WINDOW),
            budget,
        )
        short_burn = slo.burn_rate(
            telemetry.error_ratio(service, now - timedelta(hours=tier.short_window_hours), now, _SAMPLES_PER_WINDOW),
            budget,
        )
        windows.append(
            {
                "tier": tier.name,
                "long_window": _hours_label(tier.long_window_hours),
                "short_window": _hours_label(tier.short_window_hours),
                "threshold": threshold,
                "long_burn_rate": round(long_burn, 3),
                "short_burn_rate": round(short_burn, 3),
                "breached": long_burn >= threshold and short_burn >= threshold,
                "action": tier.action,
            }
        )

    window_ratio = telemetry.error_ratio(service, now - timedelta(days=window_days), now, window_days * 24 + 1)
    consumed = slo.budget_consumed(window_ratio, budget)
    remaining = 1.0 - consumed
    current_burn = windows[0]["long_burn_rate"]
    exhaustion = slo.hours_to_exhaustion(remaining, current_burn, window_days)

    breached = [w for w in windows if w["breached"]]
    if any(w["action"] == "page" for w in breached):
        recommendation = "page"
    elif breached:
        recommendation = "ticket"
    else:
        recommendation = "none"

    if breached:
        worst = breached[0]
        assessment = (
            f"{service} is burning its {target}% error budget at {current_burn:.1f}x the sustainable rate (1h). "
            f"The {worst['tier']}-burn tier is breached on both its {worst['long_window']} and "
            f"{worst['short_window']} windows (threshold {worst['threshold']:g}x), which calls for a "
            f"{worst['action']}."
        )
    else:
        assessment = (
            f"{service} is burning its {target}% error budget at {current_burn:.2f}x the sustainable rate (1h); "
            f"no burn-rate tier is breached, so by error budget alone no page or ticket is warranted."
        )
    if exhaustion is not None and remaining > 0:
        assessment += f" At the current rate the remaining budget lasts about {exhaustion:.1f} hours."
    if remaining <= 0:
        assessment += " The error budget for the window is already exhausted."

    return {
        "service": service,
        "slo_target_percent": target,
        "window_days": window_days,
        "error_budget_fraction": round(budget, 6),
        "allowed_downtime_minutes": round(budget * window_days * 24 * 60, 1),
        "budget_consumed_fraction": round(consumed, 4),
        "budget_remaining_fraction": round(remaining, 4),
        "exhausted": remaining <= 0,
        "current_burn_rate": current_burn,
        "time_to_exhaustion_hours": None if exhaustion is None else round(exhaustion, 1),
        "windows": windows,
        "recommendation": recommendation,
        "highest_breached_tier": breached[0]["tier"] if breached else None,
        "basis": "threshold = budget_consumed x (window_days x 24) / long_window_hours; burn rate = error ratio / "
                 "error budget fraction",
        "assessment": assessment,
    }
