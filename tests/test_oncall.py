import json
import socket
from datetime import datetime, timedelta, timezone

import pytest

from meridian.oncall import OnCallDirectory, Pager
from meridian.tools import Toolset, ToolError

UTC = timezone.utc
SATURDAY_MORNING = datetime(2026, 3, 14, 14, 32, tzinfo=UTC)  # 10:32 in New York, 07:32 in Los Angeles


@pytest.fixture(scope="module")
def directory(s_catalog):
    return OnCallDirectory(s_catalog)


def call(ctx, name, /, **kwargs):
    return Toolset(ctx).functions[name](**kwargs)


# ------------------------------------------------------------------ directory


def test_rotations_come_from_the_catalog(directory, s_catalog):
    expected = {e.oncall_rotation for e in s_catalog.values() if e.oncall_rotation}

    assert {r.rotation for r in directory.rotations} == expected and len(expected) == 9


def test_every_internal_service_is_owned_by_exactly_one_rotation(directory, s_catalog):
    owned = [s for r in directory.rotations for s in r.services]

    assert len(owned) == len(set(owned))
    assert set(owned) == {n for n, e in s_catalog.items() if e.oncall_rotation}


def test_third_party_services_belong_to_no_rotation(directory):
    assert not any("stripe-gateway" in r.services for r in directory.rotations)


def test_a_rotation_resolves_by_rotation_name_or_team_name_in_any_case(directory):
    assert directory.resolve("payments-oncall").team == "payments-platform"
    assert directory.resolve("Payments-Platform").rotation == "payments-oncall"
    assert directory.resolve("  DATA-ONCALL ").team == "data-platform"
    assert directory.resolve("nope") is None and directory.resolve("stripe-gateway") is None


def test_valid_names_lists_both_spellings(directory):
    names = directory.valid_names()

    assert "data-oncall" in names and "data-platform" in names and names == sorted(names)


def test_rosters_are_five_distinct_people_and_the_manager_is_separate(directory):
    for rotation in directory.rotations:
        assert len(rotation.roster) == 5 and len({p.handle for p in rotation.roster}) == 5


def test_every_team_has_a_known_timezone(directory):
    for rotation in directory.rotations:
        assert rotation.timezone != "UTC", rotation.team


# ------------------------------------------------------------------ the schedule


def test_the_shift_is_deterministic_and_secondary_differs_from_primary(directory):
    rotation = directory.resolve("data-oncall")

    first, again = directory.shift(rotation, SATURDAY_MORNING), directory.shift(rotation, SATURDAY_MORNING)

    assert first == again and first.primary != first.secondary
    assert first.secondary == rotation.roster[(rotation.roster.index(first.primary) + 1) % 5]


def test_a_shift_runs_a_week_from_monday_0900_utc(directory):
    shift = directory.shift(directory.resolve("data-oncall"), SATURDAY_MORNING)

    assert shift.starts == datetime(2026, 3, 9, 9, 0, tzinfo=UTC) and shift.ends == shift.starts + timedelta(days=7)
    assert shift.starts <= SATURDAY_MORNING < shift.ends


def test_the_handoff_happens_at_monday_0900_not_midnight(directory):
    rotation = directory.resolve("data-oncall")
    before = directory.shift(rotation, datetime(2026, 3, 16, 8, 59, tzinfo=UTC))
    after = directory.shift(rotation, datetime(2026, 3, 16, 9, 1, tzinfo=UTC))

    assert before.primary != after.primary
    assert before.ends == after.starts == datetime(2026, 3, 16, 9, 0, tzinfo=UTC)


def test_the_primary_is_constant_within_a_shift_and_rotates_across_weeks(directory):
    rotation = directory.resolve("data-oncall")
    monday = datetime(2026, 3, 9, 9, 30, tzinfo=UTC)

    within = {directory.shift(rotation, monday + timedelta(days=d)).primary for d in range(0, 7) if d < 6}
    across = {directory.shift(rotation, monday + timedelta(weeks=w)).primary for w in range(5)}

    assert len(within) == 1 and len(across) == 5  # every roster member gets a week in five


def test_different_rotations_are_not_in_lockstep(directory):
    positions = {
        r.rotation: r.roster.index(directory.shift(r, SATURDAY_MORNING).primary) for r in directory.rotations
    }

    assert len(set(positions.values())) > 1


@pytest.mark.parametrize(
    "team, local_hour_expected, business",
    [("payments-oncall", 10, False), ("data-oncall", 7, False)],  # Saturday: never business hours
)
def test_saturday_is_never_business_hours(directory, team, local_hour_expected, business):
    rotation = directory.resolve(team)
    local = directory.local_time(rotation, SATURDAY_MORNING)

    assert local.hour == local_hour_expected
    assert directory.is_business_hours(local) is business


def test_business_hours_are_nine_to_six_on_weekdays(directory):
    rotation = directory.resolve("payments-oncall")  # America/New_York
    tuesday = datetime(2026, 3, 10, tzinfo=UTC)

    def at(hour_utc):
        return directory.is_business_hours(directory.local_time(rotation, tuesday.replace(hour=hour_utc)))

    assert at(14) is True  # 10:00 EDT
    assert at(7) is False  # 03:00 EDT
    assert at(22) is False  # 18:00 EDT: the window is [9, 18)
    assert at(21) is True  # 17:00 EDT


def test_the_same_instant_is_a_different_local_time_per_team(directory):
    ny = directory.local_time(directory.resolve("payments-oncall"), SATURDAY_MORNING)
    la = directory.local_time(directory.resolve("data-oncall"), SATURDAY_MORNING)

    assert ny.hour - la.hour == 3


# ------------------------------------------------------------------------ pager


def test_the_pager_records_calls_in_order_with_sequential_ids(directory):
    pager, rotation = Pager(), directory.resolve("data-oncall")
    person = directory.shift(rotation, SATURDAY_MORNING).primary

    a = pager.page(rotation, "SEV2", "first", SATURDAY_MORNING, person)
    b = pager.page(rotation, "SEV1", "second", SATURDAY_MORNING + timedelta(minutes=1), person)

    assert [r.page_id for r in pager.records] == ["sim-page-0001", "sim-page-0002"] and pager.records == [a, b]
    assert a.simulated is True


def test_a_repeat_within_the_window_is_flagged_as_a_duplicate_but_still_recorded(directory):
    pager, rotation = Pager(), directory.resolve("data-oncall")
    person = directory.shift(rotation, SATURDAY_MORNING).primary

    first = pager.page(rotation, "SEV2", "m", SATURDAY_MORNING, person)
    repeat = pager.page(rotation, "SEV2", "m", SATURDAY_MORNING + timedelta(minutes=14), person)
    later = pager.page(rotation, "SEV2", "m", SATURDAY_MORNING + timedelta(minutes=30), person)

    assert (first.deduplicated, repeat.deduplicated, later.deduplicated) == (False, True, False)
    assert len(pager.records) == 3


def test_duplicates_are_per_rotation_and_per_severity(directory):
    pager = Pager()
    data, edge = directory.resolve("data-oncall"), directory.resolve("edge-oncall")
    person = directory.shift(data, SATURDAY_MORNING).primary
    pager.page(data, "SEV2", "m", SATURDAY_MORNING, person)

    other_team = pager.page(edge, "SEV2", "m", SATURDAY_MORNING, person)
    other_severity = pager.page(data, "SEV1", "m", SATURDAY_MORNING, person)

    assert not other_team.deduplicated and not other_severity.deduplicated


def test_pager_records_is_a_copy(directory):
    pager = Pager()

    pager.records.append("tamper")

    assert pager.records == []


# ------------------------------------------------------------------- get_oncall


def test_get_oncall_returns_the_schedule(s_ctx):
    result = call(s_ctx, "get_oncall", team="data-platform")

    assert result["rotation"] == "data-oncall" and result["team"] == "data-platform"
    assert result["primary"]["handle"] != result["secondary"]["handle"]
    assert set(result["primary"]) == {"name", "handle"}
    assert {"starts", "ends"} == set(result["shift"]) and result["as_of"] == "2026-03-14T14:32:00Z"
    assert "postgres-primary" in result["services_owned"]
    json.dumps(result)


def test_get_oncall_says_whether_it_is_business_hours_for_that_team(s_ctx):
    result = call(s_ctx, "get_oncall", team="data-oncall")

    assert result["local_time"].startswith("Saturday 07:32") and result["is_local_business_hours"] is False


def test_get_oncall_accepts_either_spelling_and_agrees(s_ctx):
    assert call(s_ctx, "get_oncall", team="payments-oncall") == call(s_ctx, "get_oncall", team="Payments-Platform")


def test_get_oncall_unknown_team_lists_the_valid_names(s_ctx):
    with pytest.raises(ToolError) as exc:
        call(s_ctx, "get_oncall", team="stripe-gateway")

    assert "No on-call rotation for 'stripe-gateway'" in str(exc.value) and "data-oncall" in str(exc.value)


def test_looking_someone_up_pages_nobody(s_ctx):
    ctx = s_ctx.with_scenario(None)

    call(ctx, "get_oncall", team="data-oncall")

    assert ctx.pager.records == []


# ------------------------------------------------------------------ page_oncall

MESSAGE = "orders-service error rate at 12% since 14:20, suspected postgres-primary connection pool; no deploy found"


def test_page_oncall_records_the_page_and_reports_it_as_simulated(s_ctx):
    ctx = s_ctx.with_scenario(None)

    result = call(ctx, "page_oncall", team="data-oncall", severity="SEV2", message=MESSAGE)

    assert result["simulated"] is True and result["delivered"] is False
    assert result["page_id"] == "sim-page-0001" and result["rotation"] == "data-oncall"
    assert result["paged"] == call(ctx, "get_oncall", team="data-oncall")["primary"]
    assert result["severity"] == "SEV2" and result["message"] == MESSAGE and result["deduplicated"] is False
    assert len(ctx.pager.records) == 1 and ctx.pager.records[0].message == MESSAGE
    json.dumps(result)


def test_page_oncall_sends_nothing_over_the_network(s_ctx, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("page_oncall attempted a network connection")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)

    result = call(s_ctx.with_scenario(None), "page_oncall", team="data-oncall", severity="SEV1", message=MESSAGE)

    assert result["delivered"] is False


def test_paging_outside_local_business_hours_warns_that_it_would_wake_someone(s_ctx):
    result = call(s_ctx.with_scenario(None), "page_oncall", team="data-oncall", severity="SEV2", message=MESSAGE)

    assert any("would wake them" in w for w in result["warnings"])


@pytest.mark.parametrize("severity", ["SEV3", "SEV4"])
def test_paging_for_a_minor_severity_warns_that_a_ticket_is_the_right_channel(s_ctx, severity):
    result = call(s_ctx.with_scenario(None), "page_oncall", team="data-oncall", severity=severity, message=MESSAGE)

    assert any("ticket" in w for w in result["warnings"])


def test_major_severities_do_not_get_the_minor_severity_warning(s_ctx):
    result = call(s_ctx.with_scenario(None), "page_oncall", team="data-oncall", severity="SEV1", message=MESSAGE)

    assert not any("ticket" in w for w in result["warnings"])


def test_a_repeat_page_is_recorded_but_flagged(s_ctx):
    ctx = s_ctx.with_scenario(None)

    call(ctx, "page_oncall", team="data-oncall", severity="SEV2", message=MESSAGE)
    repeat = call(ctx, "page_oncall", team="data-platform", severity="SEV2", message=MESSAGE)  # other spelling, same rotation

    assert repeat["deduplicated"] is True and any("already paged" in w for w in repeat["warnings"])
    assert len(ctx.pager.records) == 2


def test_each_investigation_gets_its_own_pager(s_ctx, s_scenarios):
    first = s_ctx.with_scenario(next(iter(s_scenarios.values())))
    second = first.with_scenario(first.scenario)

    call(first, "page_oncall", team="data-oncall", severity="SEV2", message=MESSAGE)

    assert len(first.pager.records) == 1 and second.pager.records == []


def test_page_oncall_uses_the_incidents_clock_for_the_timestamp(find_scenario, ctx_for):
    sc = find_scenario()
    ctx = ctx_for(sc.incident_id)

    result = call(ctx, "page_oncall", team="data-oncall", severity="SEV2", message=MESSAGE)

    assert result["paged_at"] == sc.now.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_page_oncall_unknown_team_is_rejected_without_recording(s_ctx):
    ctx = s_ctx.with_scenario(None)

    with pytest.raises(ToolError, match="No on-call rotation"):
        call(ctx, "page_oncall", team="nobody", severity="SEV1", message=MESSAGE)

    assert ctx.pager.records == []


@pytest.mark.parametrize(
    "kwargs, fragment",
    [
        ({"severity": "SEV9", "message": MESSAGE}, "severity"),
        ({"severity": "SEV1", "message": "too short"}, "message"),
        ({"severity": "SEV1", "message": "x" * 501}, "message"),
    ],
)
def test_page_oncall_rejects_bad_arguments_without_recording(s_ctx, kwargs, fragment):
    ctx = s_ctx.with_scenario(None)

    with pytest.raises(ToolError, match=fragment):
        call(ctx, "page_oncall", team="data-oncall", **kwargs)

    assert ctx.pager.records == []
