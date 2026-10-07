"""Synthetic on-call rotations and a simulated pager.

Rotations come from the service catalog (`oncall_rotation` / `owner`); the
people are invented and the schedule is a pure function of the date, so the
same instant always has the same primary. The Pager only *records* pages in
memory -- nothing here imports a network library, and a test asserts that
paging opens no sockets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from meridian.catalog import ServiceEntry
from meridian.telemetry import rng

# Where each team sits, so "is it the middle of the night for them" has an answer.
TEAM_TIMEZONES = {
    "edge-platform": "America/New_York",
    "payments-platform": "America/New_York",
    "commerce-platform": "America/Los_Angeles",
    "identity-platform": "Europe/London",
    "growth-platform": "America/Chicago",
    "data-platform": "America/Los_Angeles",
    "ai-platform": "America/Los_Angeles",
    "fulfilment-platform": "America/Chicago",
    "platform-infra": "Europe/Berlin",
}
_DEFAULT_TZ = "UTC"

_FIRST = ["Avery", "Blake", "Casey", "Devon", "Emery", "Finley", "Harper", "Jordan", "Kai", "Logan", "Morgan", "Noor",
          "Parker", "Quinn", "Riley", "Sasha", "Tatum", "Wren"]
_LAST = ["Abara", "Brandt", "Castillo", "Dhillon", "Ellison", "Fujita", "Gallo", "Haas", "Iyer", "Jansen", "Kovac",
         "Lindgren", "Mbeki", "Nakamura", "Okonkwo", "Pereira"]
_ROSTER_SIZE = 5
HANDOFF_WEEKDAY_HOUR_UTC = 9  # Monday 09:00 UTC


@dataclass(frozen=True)
class Person:
    name: str
    handle: str


@dataclass(frozen=True)
class Rotation:
    rotation: str  # e.g. "payments-oncall"
    team: str  # e.g. "payments-platform"
    timezone: str
    services: tuple[str, ...]
    roster: tuple[Person, ...]
    manager: Person


@dataclass(frozen=True)
class Shift:
    primary: Person
    secondary: Person
    starts: datetime
    ends: datetime


def _person(*key) -> Person:
    first = rng.choice(_FIRST, *key, "first")
    last = rng.choice(_LAST, *key, "last")
    return Person(name=f"{first} {last}", handle=f"{first[0].lower()}.{last.lower()}")


class OnCallDirectory:
    def __init__(self, catalog: dict[str, ServiceEntry]) -> None:
        owned: dict[tuple[str, str], list[str]] = {}
        for name, entry in sorted(catalog.items()):
            if entry.oncall_rotation:
                owned.setdefault((entry.oncall_rotation, entry.owner), []).append(name)

        self._rotations: dict[str, Rotation] = {}
        for (rotation, team), services in owned.items():
            roster, seen = [], set()
            for i in range(_ROSTER_SIZE * 3):  # re-draw on a name collision within the roster
                person = _person(rotation, "roster", i)
                if person.handle not in seen:
                    seen.add(person.handle)
                    roster.append(person)
                if len(roster) == _ROSTER_SIZE:
                    break
            self._rotations[rotation] = Rotation(
                rotation=rotation,
                team=team,
                timezone=TEAM_TIMEZONES.get(team, _DEFAULT_TZ),
                services=tuple(services),
                roster=tuple(roster),
                manager=_person(rotation, "manager"),
            )

    @property
    def rotations(self) -> list[Rotation]:
        return sorted(self._rotations.values(), key=lambda r: r.rotation)

    def valid_names(self) -> list[str]:
        """Every accepted spelling: rotation names and owning-team names."""
        return sorted({r.rotation for r in self.rotations} | {r.team for r in self.rotations})

    def resolve(self, team_or_rotation: str) -> Rotation | None:
        wanted = team_or_rotation.strip().lower()
        for rotation in self._rotations.values():
            if wanted in (rotation.rotation.lower(), rotation.team.lower()):
                return rotation
        return None

    def shift(self, rotation: Rotation, at: datetime) -> Shift:
        monday = (at - timedelta(days=at.weekday())).replace(
            hour=HANDOFF_WEEKDAY_HOUR_UTC, minute=0, second=0, microsecond=0
        )
        if at < monday:  # Monday before the 09:00 handoff still belongs to last week's shift
            monday -= timedelta(days=7)
        week = monday.toordinal() // 7
        offset = int(rng.unit(rotation.rotation, "offset") * len(rotation.roster))
        index = (week + offset) % len(rotation.roster)
        return Shift(
            primary=rotation.roster[index],
            secondary=rotation.roster[(index + 1) % len(rotation.roster)],
            starts=monday,
            ends=monday + timedelta(days=7),
        )

    @staticmethod
    def local_time(rotation: Rotation, at: datetime) -> datetime:
        return at.astimezone(ZoneInfo(rotation.timezone))

    @staticmethod
    def is_business_hours(local: datetime) -> bool:
        return local.weekday() < 5 and 9 <= local.hour < 18


@dataclass(frozen=True)
class PageRecord:
    page_id: str
    at: datetime
    rotation: str
    team: str
    severity: str
    message: str
    paged: Person
    deduplicated: bool  # same rotation+severity already paged within the window
    simulated: bool = True  # always: nothing is ever delivered


class Pager:
    """Records page requests. Sends nothing, anywhere."""

    def __init__(self, dedupe_window: timedelta = timedelta(minutes=15)) -> None:
        self._dedupe_window = dedupe_window
        self._records: list[PageRecord] = []

    @property
    def records(self) -> list[PageRecord]:
        return list(self._records)

    def page(self, rotation: Rotation, severity: str, message: str, at: datetime, paged: Person) -> PageRecord:
        duplicate = any(
            r.rotation == rotation.rotation and r.severity == severity and timedelta(0) <= at - r.at < self._dedupe_window
            for r in self._records
        )
        record = PageRecord(
            page_id=f"sim-page-{len(self._records) + 1:04d}",
            at=at,
            rotation=rotation.rotation,
            team=rotation.team,
            severity=severity,
            message=message,
            paged=paged,
            deduplicated=duplicate,
        )
        self._records.append(record)
        return record
