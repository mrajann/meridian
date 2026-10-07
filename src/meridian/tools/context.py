"""Everything a tool needs, bound once per investigation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from meridian.catalog import ServiceEntry
from meridian.graph import DependencyGraph
from meridian.oncall import OnCallDirectory, Pager
from meridian.retrieval import Retriever
from meridian.telemetry import Scenario, Telemetry


@dataclass
class ToolContext:
    catalog: dict[str, ServiceEntry]
    graph: DependencyGraph
    retriever: Retriever
    telemetry: Telemetry
    oncall: OnCallDirectory
    pager: Pager = field(default_factory=Pager)

    @property
    def scenario(self) -> Scenario | None:
        return self.telemetry.scenario

    @property
    def now(self) -> datetime:
        return self.telemetry.now

    @property
    def excluded_doc_ids(self) -> frozenset[str]:
        """Corpus documents the active incident must not be able to retrieve:
        its own alert, and (for cascades) the postmortem that is only written
        after it is resolved. Retrieving either would hand over the answer."""
        return self.scenario.excluded_doc_ids if self.scenario else frozenset()

    def with_scenario(self, scenario: Scenario | None) -> ToolContext:
        """A context for investigating one incident: its own telemetry and a
        fresh pager, so pages from one run never appear in another's."""
        return replace(self, telemetry=Telemetry(self.catalog, scenario), pager=Pager())


def build_context(
    catalog: dict[str, ServiceEntry], retriever: Retriever, scenario: Scenario | None = None
) -> ToolContext:
    return ToolContext(
        catalog=catalog,
        graph=DependencyGraph(catalog),
        retriever=retriever,
        telemetry=Telemetry(catalog, scenario),
        oncall=OnCallDirectory(catalog),
    )
