"""Tools that read the service catalog and dependency graph."""

from __future__ import annotations

import difflib
from typing import Annotated, Any

from pydantic import Field

from meridian.catalog import ServiceEntry
from meridian.tools.context import ToolContext
from meridian.tools.errors import ToolError
from meridian.tools.registry import tool

ServiceName = Annotated[str, Field(min_length=1, max_length=100)]


def require_service(ctx: ToolContext, name: str) -> ServiceEntry:
    entry = ctx.catalog.get(name.strip().lower())
    if entry is None:
        close = difflib.get_close_matches(name.strip().lower(), ctx.catalog, n=4, cutoff=0.5)
        hint = f" Did you mean: {', '.join(close)}?" if close else ""
        raise ToolError(
            f"No service named '{name}' in the current catalog.{hint} A name that is simply not in the catalog "
            f"is often a decommissioned service referenced by an outdated runbook."
        )
    return entry


def _summary(entry: ServiceEntry) -> dict[str, Any]:
    return {"name": entry.name, "tier": entry.tier, "owner": entry.owner, "external": entry.tier == "external"}


@tool
def get_service(ctx: ToolContext, name: ServiceName) -> dict:
    """Look up one service in the catalog: tier, owner, on-call rotation, SLO, dependencies, and blast radius.

    Use this to learn what a service is and how critical it is before reasoning about an incident on it, to find
    out who owns it (the `oncall_rotation` is what get_oncall and page_oncall take), and to check whether a
    service named in a runbook or alert still exists. A name that is not found is meaningful: it usually means a
    decommissioned service, so a runbook that tells you to operate it is stale.

    Tier 1 services are revenue- or login-critical, tier 2 important, tier 3 internal tooling; "external" means a
    third-party vendor Meridian does not operate (it has no on-call rotation, and its failures cannot be fixed
    internally). `business_hours_only` services do not warrant waking someone at night. `runbooks` lists catalog
    labels, not documents -- use search_runbooks to read actual runbook content.

    Do not use this to see what depends on a service or what it depends on beyond one hop (use get_dependents and
    get_dependencies, which can walk several hops).

    Args:
        name: Exact service name, lowercase with hyphens, e.g. "checkout-api" or "postgres-primary".

    Returns:
        name, tier, owner, oncall_rotation (null for external), description, depends_on, depended_on_by,
        slo (availability_percent, latency_p99_ms), runbooks, blast_radius, business_hours_only, external.
    """
    entry = require_service(ctx, name)
    return {
        "name": entry.name,
        "tier": entry.tier,
        "owner": entry.owner,
        "oncall_rotation": entry.oncall_rotation,
        "description": entry.description,
        "depends_on": entry.depends_on,
        "depended_on_by": entry.depended_on_by,
        "slo": {"availability_percent": entry.slo.availability, "latency_p99_ms": entry.slo.latency_p99_ms},
        "runbooks": entry.runbooks,
        "blast_radius": entry.blast_radius,
        "business_hours_only": entry.business_hours_only,
        "external": entry.tier == "external",
    }


def _walk(ctx: ToolContext, name: str, depth: int, direction: str) -> dict:
    name = require_service(ctx, name).name
    hops = (
        ctx.graph.dependencies_with_hops(name, depth)
        if direction == "dependencies"
        else ctx.graph.dependents_with_hops(name, depth)
    )
    services = [
        {"hops": distance, **_summary(ctx.catalog[service])}
        for service, distance in sorted(hops.items(), key=lambda item: (item[1], item[0]))
    ]
    by_hop: dict[str, list[str]] = {}
    for item in services:
        by_hop.setdefault(str(item["hops"]), []).append(item["name"])
    return {"service": name, "direction": direction, "depth": depth, "count": len(services),
            "services": services, "by_hop": by_hop}


@tool
def get_dependencies(
    ctx: ToolContext, name: ServiceName, depth: Annotated[int, Field(ge=1, le=10)] = 1
) -> dict:
    """List what a service depends on -- the upstream things whose failure can make it fail.

    Use this to work out where a problem could originate: if checkout-api is failing, its dependencies are the
    candidates (database, payment processor, auth, ...). Start with depth 1 (direct dependencies); raise it to
    follow the chain (a database problem may sit two hops behind the service you were paged for). A burst of
    simultaneous alerts across seemingly unrelated services usually shares a dependency: call this on a few of
    them and look for the service that appears in all of the lists.

    Entries marked external are third-party vendors; if one of those is the root cause there is nothing to fix
    internally, only to mitigate and communicate.

    Do not use this to find what is affected when a service fails (that is the opposite direction: use
    get_dependents).

    Args:
        name: Exact service name, e.g. "orders-service".
        depth: How many hops to follow, 1 to 10. 1 is direct dependencies only.

    Returns:
        service, direction, depth, count, services (each with hops, name, tier, owner, external) ordered nearest
        first, and by_hop mapping hop distance to names.
    """
    return _walk(ctx, name, depth, "dependencies")


@tool
def get_dependents(
    ctx: ToolContext, name: ServiceName, depth: Annotated[int, Field(ge=1, le=10)] = 1
) -> dict:
    """List what depends on a service -- the blast radius if it fails.

    Use this to size an incident: given a failing service, which services (and so which customer-facing
    features) are affected. Use depth 1 for direct callers and a larger depth for the full cascade, e.g. a
    failure in postgres-primary reaches most of the platform within three hops. It is also how you test a
    hypothesis about a shared root cause: if the services alerting together are all dependents of one suspect,
    that suspect is a strong candidate.

    Do not use this to ask what a service itself needs in order to work (use get_dependencies). Being a
    dependent means a service can be affected, not that it is: confirm with query_metrics.

    Args:
        name: Exact service name, e.g. "postgres-primary".
        depth: How many hops to follow, 1 to 10. 1 is direct dependents only; use 10 for the complete set.

    Returns:
        service, direction, depth, count, services (each with hops, name, tier, owner, external) ordered nearest
        first, and by_hop mapping hop distance to names.
    """
    return _walk(ctx, name, depth, "dependents")
