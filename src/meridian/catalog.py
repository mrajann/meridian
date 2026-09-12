"""Service catalog: schema, loading, and cross-reference validation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

CATALOG_DIR = Path(__file__).resolve().parents[2] / "catalog" / "services"

Tier = Literal[1, 2, 3, "external"]


class ServiceSLO(BaseModel):
    availability: float
    latency_p99_ms: int | None = None


class ServiceEntry(BaseModel):
    name: str
    tier: Tier
    owner: str
    oncall_rotation: str | None = None
    description: str
    depends_on: list[str] = Field(default_factory=list)
    depended_on_by: list[str] = Field(default_factory=list)
    slo: ServiceSLO
    runbooks: list[str] = Field(default_factory=list)
    blast_radius: str
    business_hours_only: bool = False

    @field_validator("name")
    @classmethod
    def name_is_kebab_case(cls, value: str) -> str:
        if not value or value != value.lower() or " " in value or "_" in value:
            raise ValueError(f"service name must be lowercase kebab-case: {value!r}")
        return value


def load_catalog(directory: Path = CATALOG_DIR) -> dict[str, ServiceEntry]:
    """Load every service entry in `directory`, validating cross-references.

    Raises ValueError if any two entries disagree about a dependency edge.
    """
    catalog: dict[str, ServiceEntry] = {}

    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        entry = ServiceEntry.model_validate(data)
        if entry.name in catalog:
            raise ValueError(f"duplicate service name {entry.name!r} (in {path})")
        catalog[entry.name] = entry

    errors = validate_consistency(catalog)
    if errors:
        raise ValueError("catalog consistency errors:\n" + "\n".join(errors))

    return catalog


def validate_consistency(catalog: dict[str, ServiceEntry]) -> list[str]:
    """Check that depends_on and depended_on_by agree with each other.

    For every edge A -> B in A.depends_on, B.depended_on_by must list A,
    and vice versa. Also flags references to services absent from the catalog.
    Returns a list of human-readable problem descriptions (empty if none).
    """
    errors: list[str] = []

    for name, entry in catalog.items():
        for dep in entry.depends_on:
            if dep not in catalog:
                errors.append(f"{name}: depends_on unknown service {dep!r}")
            elif name not in catalog[dep].depended_on_by:
                errors.append(
                    f"{name}: depends_on {dep!r}, but {dep!r} does not list "
                    f"{name!r} in depended_on_by"
                )

        for dependent in entry.depended_on_by:
            if dependent not in catalog:
                errors.append(f"{name}: depended_on_by unknown service {dependent!r}")
            elif name not in catalog[dependent].depends_on:
                errors.append(
                    f"{name}: depended_on_by {dependent!r}, but {dependent!r} "
                    f"does not list {name!r} in depends_on"
                )

    return errors
