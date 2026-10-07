"""The synthetic world as the tools see it: metric series and deploy history
for one point in time, optionally containing one incident."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from meridian.catalog import ServiceEntry
from meridian.telemetry import metrics, rng
from meridian.telemetry.deploys import DeployRecord, deploys_between
from meridian.telemetry.scenario import Scenario

UTC = timezone.utc
# "Now" when no incident is active: the timestamp from the spec's eval example.
DEFAULT_NOW = datetime(2026, 3, 14, 14, 32, tzinfo=UTC)


@dataclass(frozen=True)
class Sample:
    t: datetime
    value: float
    expected: float


def _instants(start: datetime, end: datetime, n: int) -> list[datetime]:
    """n evenly spaced instants from start to end inclusive. Computed from the
    total span in microseconds, not by accumulating a rounded step, so the
    last one is exactly `end` (it is "now", and must read as now)."""
    total = (end - start) // timedelta(microseconds=1)
    if n == 1:
        return [start]
    return [start + timedelta(microseconds=round(total * i / (n - 1))) for i in range(n)]


class Telemetry:
    def __init__(self, catalog: dict[str, ServiceEntry], scenario: Scenario | None = None) -> None:
        self._catalog = catalog
        self.scenario = scenario

    @property
    def now(self) -> datetime:
        return self.scenario.now if self.scenario else DEFAULT_NOW

    def available_metrics(self, service: str) -> list[str]:
        return metrics.available_metrics(self._catalog, service)

    def value_at(self, service: str, metric: str, t: datetime) -> Sample:
        expected = metrics.expected(self._catalog, service, metric, t)
        seed = self.scenario.seed if self.scenario else "healthy"
        minute = int(t.timestamp() // 60)  # noise is per-minute, so overlapping queries agree
        value = expected * (1.0 + metrics.METRICS[metric].noise * rng.gauss(seed, service, metric, minute))

        scenario = self.scenario
        if scenario is not None:
            since_onset = (t - scenario.onset).total_seconds() / 60.0
            for effect, amplitude, lag in scenario.effects_for(service):
                if effect.metric == metric:
                    value = effect.apply(value, since_onset - lag, amplitude)
            blip = scenario.blip
            if (
                blip is not None
                and blip.service == service
                and blip.metric == metric
                and blip.start <= t < blip.start + timedelta(minutes=blip.minutes)
            ):
                value *= blip.multiplier

        return Sample(t=t, value=metrics.clip(metric, value), expected=expected)

    def series(self, service: str, metric: str, start: datetime, end: datetime, n_points: int = 96) -> list[Sample]:
        return [self.value_at(service, metric, t) for t in _instants(start, end, n_points)]

    def error_ratio(self, service: str, start: datetime, end: datetime, n_points: int = 96) -> float:
        """Share of requests that failed over [start, end], weighted by
        request volume (a busy minute counts for more than a quiet one)."""
        failed = total = 0.0
        for t in _instants(start, end, n_points):
            requests = self.value_at(service, "request_rate_rps", t).value
            failed += self.value_at(service, "error_rate", t).value * requests
            total += requests
        return failed / total if total else 0.0

    def deploys(self, service: str, start: datetime, end: datetime) -> list[DeployRecord]:
        return deploys_between(self._catalog, self.scenario, service, start, end)
