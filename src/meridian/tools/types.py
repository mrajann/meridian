"""Parameter types for tools.

Every string parameter of a tool must declare what *kind* of string it is, and
the kind decides how it is handled -- once, in one place, not in each tool:

- `CatalogEntity` (ServiceName, TeamName): an identifier looked up in the
  catalog or on-call directory. It is normalized (whitespace stripped, case
  folded) by the argument-validation step every call passes through, so a tool
  body only ever sees the canonical form. A model sending "Checkout-API" or
  " CHECKOUT-API " cannot reach tool code in any other spelling.
- `Verbatim` (SearchText, Message, Window): free text or a structured string
  that is used exactly as given.

`registry.tool` refuses a tool with a string parameter that declares neither,
so there is no way to forget: a bare `service: str` fails at import with
instructions. Writing tool twelve takes one explicit choice, not a recalled
convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field


def normalize_identifier(value):
    """The one canonical form of a catalog identifier. Non-strings pass
    through untouched so validation can report the type error itself."""
    return value.strip().lower() if isinstance(value, str) else value


@dataclass(frozen=True)
class CatalogEntity:
    """Marks a parameter as a catalog identifier (normalized on the way in)."""

    kind: Literal["service", "team"]


@dataclass(frozen=True)
class Verbatim:
    """Marks a string parameter as free text, used exactly as given."""


def _entity(kind: Literal["service", "team"]):
    # BeforeValidator first so the length bounds apply to the normalized
    # value: a whitespace-only name is empty, not one character long.
    return Annotated[
        str, BeforeValidator(normalize_identifier), Field(min_length=1, max_length=100), CatalogEntity(kind)
    ]


ServiceName = _entity("service")
TeamName = _entity("team")

SearchText = Annotated[str, Field(min_length=3, max_length=500), Verbatim()]
Message = Annotated[str, Field(min_length=20, max_length=500), Verbatim()]
Window = Annotated[str, Field(pattern=r"^\d+[mhd]$"), Verbatim()]

# Parameter names that refer to catalog entities. A tool using one of these
# names for a Verbatim string is almost certainly misclassifying it.
ENTITY_PARAMETER_NAMES = frozenset({"service", "services", "team"})
