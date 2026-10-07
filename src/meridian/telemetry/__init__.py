"""Synthetic but realistic telemetry (metric series, deploy records) for the
tool layer to query. Deterministic and offline -- see rng.py."""

from meridian.telemetry.deploys import DeployRecord
from meridian.telemetry.metrics import METRICS, available_metrics
from meridian.telemetry.scenario import Scenario, build_scenarios, scenario_from_alert
from meridian.telemetry.world import DEFAULT_NOW, Sample, Telemetry

__all__ = [
    "DEFAULT_NOW",
    "DeployRecord",
    "METRICS",
    "Sample",
    "Scenario",
    "Telemetry",
    "available_metrics",
    "build_scenarios",
    "scenario_from_alert",
]
