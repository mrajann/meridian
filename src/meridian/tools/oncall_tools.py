"""get_oncall and page_oncall (the latter is simulated)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from meridian.oncall import Rotation
from meridian.tools.context import ToolContext
from meridian.tools.errors import ToolError
from meridian.tools.registry import tool

TeamName = Annotated[str, Field(min_length=1, max_length=100)]
Severity = Literal["SEV1", "SEV2", "SEV3", "SEV4"]


def _rotation(ctx: ToolContext, team: str) -> Rotation:
    rotation = ctx.oncall.resolve(team)
    if rotation is None:
        raise ToolError(f"No on-call rotation for '{team}'. Valid names: {', '.join(ctx.oncall.valid_names())}")
    return rotation


def _person(p) -> dict:
    return {"name": p.name, "handle": p.handle}


@tool
def get_oncall(ctx: ToolContext, team: TeamName) -> dict:
    """Look up who is on call for a team right now, and whether it is the middle of their night.

    Use this to decide who to page and how disruptive paging would be: it returns the primary and secondary
    on-call, the escalation manager, and the team's local time with a flag for whether it falls in local business
    hours (Monday-Friday, 09:00-18:00). Accepts either the on-call rotation name from get_service (e.g.
    "payments-oncall") or the owning team's name (e.g. "payments-platform").

    Looking someone up does not contact them. Do not use this to actually notify anyone (use page_oncall), and
    note that third-party vendors have no rotation here: if the root cause is a vendor, page the internal team
    that owns the integration, not the vendor.

    Args:
        team: On-call rotation name or owning team name, e.g. "data-oncall" or "data-platform".

    Returns:
        team, rotation, timezone, services_owned, primary and secondary (name, handle), escalation_manager,
        shift (starts, ends), local_time, is_local_business_hours, and as_of.
    """
    rotation = _rotation(ctx, team)
    shift = ctx.oncall.shift(rotation, ctx.now)
    local = ctx.oncall.local_time(rotation, ctx.now)
    return {
        "team": rotation.team,
        "rotation": rotation.rotation,
        "timezone": rotation.timezone,
        "services_owned": list(rotation.services),
        "primary": _person(shift.primary),
        "secondary": _person(shift.secondary),
        "escalation_manager": _person(rotation.manager),
        "shift": {"starts": shift.starts.strftime("%Y-%m-%dT%H:%M:%SZ"), "ends": shift.ends.strftime("%Y-%m-%dT%H:%M:%SZ")},
        "local_time": local.strftime("%A %H:%M %Z"),
        "is_local_business_hours": ctx.oncall.is_business_hours(local),
        "as_of": ctx.now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@tool
def page_oncall(
    ctx: ToolContext,
    team: TeamName,
    severity: Severity,
    message: Annotated[str, Field(min_length=20, max_length=500)],
) -> dict:
    """Page a team's primary on-call about an incident. SIMULATED: the request is recorded and nothing is sent.

    In a real deployment this wakes a person, so treat it as costly even though it is simulated here: call it
    once, only after you have decided paging is justified (see compute_error_budget and the service's tier and
    business_hours_only), and do not repeat it for the same incident -- repeats within 15 minutes for the same
    team and severity are recorded as duplicates. Use get_oncall first to see who would be paged and what time it
    is for them. SEV1/SEV2 are the page-worthy severities; SEV3 and SEV4 normally belong in a ticket, and paging
    for them returns a warning.

    Write the message for a human who was just woken up and has no context: what is failing, who or what is
    affected and how badly, the suspected cause and your confidence in it, and what you have already checked. A
    vague message ("service down") wastes their first ten minutes.

    Do not use this to find out who is on call (use get_oncall, which contacts no one) or to raise a ticket-level
    issue.

    Args:
        team: On-call rotation name or owning team name, e.g. "payments-oncall" or "payments-platform".
        severity: Incident severity: SEV1 (critical, revenue or login down), SEV2 (major degradation), SEV3
            (minor), SEV4 (cosmetic or informational).
        message: What the on-call needs to know, 20 to 500 characters: failure, impact, suspected cause with
            confidence, and what was already checked.

    Returns:
        page_id, simulated (always true), delivered (always false), team, rotation, who would be paged,
        severity, message, paged_at, deduplicated, and any warnings.
    """
    rotation = _rotation(ctx, team)
    shift = ctx.oncall.shift(rotation, ctx.now)
    record = ctx.pager.page(rotation, severity, message, ctx.now, shift.primary)
    local = ctx.oncall.local_time(rotation, ctx.now)

    warnings = []
    if severity in ("SEV3", "SEV4"):
        warnings.append(f"{severity} incidents normally do not warrant paging; a ticket is usually the right channel.")
    if record.deduplicated:
        warnings.append("This rotation was already paged at this severity within the last 15 minutes; recorded as a duplicate.")
    if not ctx.oncall.is_business_hours(local):
        warnings.append(f"It is {local.strftime('%A %H:%M')} local time for this team: a real page would wake them.")

    return {
        "page_id": record.page_id,
        "simulated": True,
        "delivered": False,
        "team": rotation.team,
        "rotation": rotation.rotation,
        "paged": _person(shift.primary),
        "severity": severity,
        "message": message,
        "paged_at": record.at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "deduplicated": record.deduplicated,
        "warnings": warnings,
    }
