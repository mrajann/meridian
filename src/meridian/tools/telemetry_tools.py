"""Tools that read the (synthetic) live telemetry: metric series and deploys."""

from __future__ import annotations

import math
import re
import statistics
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from pydantic import Field

from meridian.telemetry.metrics import METRICS
from meridian.tools.catalog_tools import require_service
from meridian.tools.context import ToolContext
from meridian.tools.errors import ToolError
from meridian.tools.registry import tool
from meridian.tools.types import ServiceName, Window

MetricName = Literal[
    "request_rate_rps",
    "error_rate",
    "latency_p99_ms",
    "cpu_percent",
    "memory_percent",
    "disk_used_percent",
    "connection_pool_in_use_percent",
    "queue_depth",
]

_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400}
_SAMPLES = 96  # resolution the series is generated and scanned at
_POINTS_RETURNED = 24  # what the model is shown: enough to see a shape, cheap to read
ANOMALY_HIGH, ANOMALY_LOW = 1.5, 0.5  # observed / expected beyond which a sample is "off"
ANOMALY_MIN_MINUTES = 5.0  # a deviation that has already ended must have lasted this long
ANOMALY_ONGOING_MIN_MINUTES = 2.0  # ...one still in progress counts after this long


def parse_window(window: str, *, minimum: timedelta, maximum: timedelta, label: str) -> timedelta:
    match = re.fullmatch(r"(\d+)([mhd])", window.strip())
    if not match:
        raise ToolError(f"window '{window}' is not valid; use a number and a unit, e.g. '15m', '1h', '24h', '7d'")
    span = timedelta(seconds=int(match.group(1)) * _UNIT_SECONDS[match.group(2)])
    if not minimum <= span <= maximum:
        raise ToolError(f"{label} window '{window}' is out of range; use between {_fmt(minimum)} and {_fmt(maximum)}")
    return span


def _fmt(span: timedelta) -> str:
    minutes = int(span.total_seconds() // 60)
    return f"{minutes // 1440}d" if minutes % 1440 == 0 else (f"{minutes // 60}h" if minutes % 60 == 0 else f"{minutes}m")


def _round(metric: str, value: float) -> float:
    return round(value, 5 if metric == "error_rate" else 2)


def _iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _detect_anomaly(samples, step_minutes: float) -> dict[str, Any]:
    """First sustained run of samples off from `expected` by 1.5x or more (or
    0.5x or less). A run that already ended must have lasted 5+ minutes, which
    filters out blips; one still in progress at the end of the window counts
    after 2 minutes, because an incident that has only just begun cannot yet
    have lasted long and must not be reported as "nothing wrong"."""
    found = None
    run_start = None
    for i, s in enumerate(samples + [None]):
        off = s is not None and (s.value / s.expected >= ANOMALY_HIGH or s.value / s.expected <= ANOMALY_LOW)
        if off and run_start is None:
            run_start = i
        elif not off and run_start is not None:
            ongoing = s is None
            minutes = (i - run_start) * step_minutes
            if minutes >= (ANOMALY_ONGOING_MIN_MINUTES if ongoing else ANOMALY_MIN_MINUTES):
                found = (run_start, i, ongoing)
                break
            run_start = None

    if found is None:
        return {
            "detected": False,
            "note": f"No sustained deviation (>= {ANOMALY_HIGH}x or <= {ANOMALY_LOW}x of expected, lasting "
                    f"{ANOMALY_MIN_MINUTES:g}+ minutes or still ongoing after {ANOMALY_ONGOING_MIN_MINUTES:g}). "
                    f"This does not prove nothing is wrong: some failures (degraded output quality, stale data) "
                    f"leave this metric untouched.",
        }
    first, end, ongoing = found
    ratios = [s.value / s.expected for s in samples[first:end]]
    peak = max(ratios, key=lambda r: abs(math.log(r)) if r > 0 else 99)
    return {
        "detected": True,
        "ongoing": ongoing,
        "started_at": _iso(samples[first].t),
        "direction": "above" if peak > 1 else "below",
        "peak_ratio_vs_expected": round(peak, 2),
        "note": "started_at is approximate: a gradual ramp is flagged when it crosses the threshold, "
                "slightly after it actually began.",
    }


@tool
def query_metrics(
    ctx: ToolContext,
    service: ServiceName,
    metric: MetricName,
    window: Window = "1h",
) -> dict:
    """Read a service's recent metric time series, with the expected level and an anomaly check.

    Use this to see what is actually happening on a service: is the error rate up, did latency step or ramp, is a
    pool or disk saturating, and when did it start? The window ends "now" (the moment of the investigation), so
    "1h" is the last hour. Check the service named in the alert first, then its dependencies (get_dependencies)
    and dependents (get_dependents): the service that went wrong *first* is the better root-cause candidate, and
    the onset time (`anomaly.started_at`) is what you compare against deploy times from get_deploy_history.

    Metrics: error_rate (ratio 0-1), latency_p99_ms, request_rate_rps, cpu_percent, memory_percent are available
    on every internal service; disk_used_percent, connection_pool_in_use_percent and queue_depth only on
    services that have them (asking for one a service lacks returns the valid list). Third-party services expose
    only error_rate, latency_p99_ms and request_rate_rps, as observed from Meridian's side.

    Read the result carefully. `anomaly.detected` is true only for a sustained deviation from `expected` (the
    seasonal baseline) of 1.5x or more -- and a quiet metric is not proof of health: some failures, such as
    degraded model output or stale data, leave every metric untouched, so if the alert describes a problem the
    metrics do not show, say so rather than inventing an explanation. A short single spike on a metric
    (visible in `points` and `summary.max`) that does not persist is usually noise, not the incident. Use a
    window long enough to include a quiet stretch before the problem, so the change is visible.

    Do not use this for deploys (use get_deploy_history) or to judge whether an SLO is at risk (use
    compute_error_budget).

    Args:
        service: Service name, e.g. "checkout-api".
        metric: Which metric to read; must be one this service has.
        window: How far back to look, ending now: a number and a unit, e.g. "15m", "1h", "6h", "24h", "7d".
            Between 5m and 7d. Default 1h.

    Returns:
        service, metric, unit, window, start/end timestamps, points (24 values with t, value and expected),
        summary (latest, mean, min, max, peak_at, expected_mean, latest_vs_expected), and anomaly
        (detected, started_at, direction, peak_ratio_vs_expected, note).
    """
    require_service(ctx, service)
    available = ctx.telemetry.available_metrics(service)
    if metric not in available:
        raise ToolError(f"'{service}' has no '{metric}' metric. Available for this service: {', '.join(available)}")
    span = parse_window(window, minimum=timedelta(minutes=5), maximum=timedelta(days=7), label="metric")

    end = ctx.now
    start = end - span
    samples = ctx.telemetry.series(service, metric, start, end, _SAMPLES)
    step_minutes = span.total_seconds() / 60 / (_SAMPLES - 1)

    per_point = _SAMPLES // _POINTS_RETURNED
    points = []
    for i in range(0, _SAMPLES, per_point):
        group = samples[i : i + per_point]
        points.append(
            {
                "t": _iso(group[-1].t),
                "value": _round(metric, statistics.mean(s.value for s in group)),
                "expected": _round(metric, statistics.mean(s.expected for s in group)),
            }
        )

    values = [s.value for s in samples]
    peak = max(samples, key=lambda s: s.value)
    expected_mean = statistics.mean(s.expected for s in samples)
    return {
        "service": service,
        "metric": metric,
        "unit": METRICS[metric].unit,
        "window": window,
        "start": _iso(start),
        "end": _iso(end),
        "points": points,
        "summary": {
            "latest": _round(metric, samples[-1].value),
            "mean": _round(metric, statistics.mean(values)),
            "min": _round(metric, min(values)),
            "max": _round(metric, max(values)),
            "peak_at": _iso(peak.t),
            "expected_mean": _round(metric, expected_mean),
            "latest_vs_expected": round(samples[-1].value / samples[-1].expected, 2),
        },
        "anomaly": _detect_anomaly(samples, step_minutes),
    }


@tool
def get_deploy_history(
    ctx: ToolContext,
    service: ServiceName,
    window: Window = "24h",
) -> dict:
    """List the deploys of a service within a recent window, newest first.

    Use this when an incident might be change-related: it shows what shipped and when. Then compare the deploy
    time with when the problem actually began (the onset from query_metrics), checking on the metric itself
    whether it changed at the deploy or only later, or before it.

    A deploy shortly before an incident is a lead, not an answer. Deploys are routine (most services ship several
    times a week, so expect some in any window), many incidents have no related deploy at all, and a coincidental
    deploy just before onset is common -- and the change summary is often too vague to tell a harmless change
    from a harmful one. Treat "deploy then incident" as a hypothesis, and weigh it against the failure pattern:
    a deploy cannot fill a disk, expire a certificate, or take down a third party. Look at longer windows too to
    see the normal deploy cadence. Dependencies' deploys matter as well: call this for them, not only for the
    service that alerted.

    Third-party services have no Meridian deploys and return an empty list. Do not use this for current system
    state (use query_metrics).

    Args:
        service: Service name, e.g. "checkout-api".
        window: How far back to look, ending now: a number and a unit, e.g. "6h", "24h", "7d". Between 5m and
            30d. Default 24h.

    Returns:
        service, window, start/end timestamps, count, and deploys (deploy_id, deployed_at,
        minutes_before_now, version, deployed_by, change_type, change_summary, status) newest first.
    """
    entry = require_service(ctx, service)
    span = parse_window(window, minimum=timedelta(minutes=5), maximum=timedelta(days=30), label="deploy")
    end = ctx.now
    start = end - span
    records = sorted(ctx.telemetry.deploys(service, start, end), key=lambda r: r.deployed_at, reverse=True)
    result: dict[str, Any] = {
        "service": service,
        "window": window,
        "start": _iso(start),
        "end": _iso(end),
        "count": len(records),
        "deploys": [
            {
                "deploy_id": r.deploy_id,
                "deployed_at": _iso(r.deployed_at),
                "minutes_before_now": round((end - r.deployed_at).total_seconds() / 60),
                "version": r.version,
                "deployed_by": r.deployed_by,
                "change_type": r.change_type,
                "change_summary": r.change_summary,
                "status": r.status,
            }
            for r in records
        ],
    }
    if entry.tier == "external":
        result["note"] = "Third-party service: Meridian does not deploy it, so there are no deploy records."
    return result
