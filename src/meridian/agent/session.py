"""Wiring an incident into a runnable agent: the alert, its synthetic world,
and a toolset bound to both. Shared by the CLI now and the eval harness later."""

from __future__ import annotations

from dataclasses import dataclass

from meridian.catalog import ServiceEntry, load_catalog
from meridian.config import Settings
from meridian.corpus import load_corpus
from meridian.corpus.models import CorpusDocument
from meridian.indexing.embeddings import get_embedder
from meridian.indexing.store import VectorIndex
from meridian.retrieval import Retriever
from meridian.telemetry import Scenario, build_scenarios
from meridian.tools import Toolset, build_context
from meridian.tools.context import ToolContext


@dataclass
class IncidentSession:
    alert: CorpusDocument
    scenario: Scenario
    ctx: ToolContext
    catalog: dict[str, ServiceEntry]

    def toolset(self) -> Toolset:
        return Toolset(self.ctx)

    def fresh(self) -> "IncidentSession":
        """The same incident with a new pager and telemetry, so a second run
        never sees the first run's pages."""
        return IncidentSession(self.alert, self.scenario, self.ctx.with_scenario(self.scenario), self.catalog)


def open_incidents(settings: Settings) -> dict[str, "IncidentSession"]:
    """Every alert in the on-disk corpus as a ready session. Each session has
    its own telemetry and pager; the retriever and index are shared."""
    catalog = load_catalog()
    documents = load_corpus()
    retriever = Retriever(VectorIndex(settings.chroma_persist_dir, get_embedder(settings)))
    base = build_context(catalog, retriever)
    scenarios = build_scenarios(documents, catalog)
    alerts = {d.doc_id: d for d in documents if d.doc_type == "alert"}
    return {
        incident_id: IncidentSession(alerts[incident_id], scenario, base.with_scenario(scenario), catalog)
        for incident_id, scenario in scenarios.items()
    }
