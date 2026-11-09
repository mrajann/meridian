"""What the agent has actually seen, so its citations can be checked.

A report that cites `runbook-foo` is only grounded if a search in *this*
investigation returned `runbook-foo`. The ledger records, from successful tool
results only, every document, deploy, metric series and catalog entry the
agent was shown; `report.check_report` rejects a citation that isn't in it.
This is what turns "cite your evidence" from a prompt request into a
checked property.
"""

from __future__ import annotations

from typing import Any


class EvidenceLedger:
    def __init__(self) -> None:
        self.documents: dict[str, str] = {}  # doc_id -> doc_type
        self.deploys: set[str] = set()
        self.metrics: set[str] = set()  # "service/metric"
        self.services: set[str] = set()  # catalog entries the agent looked up
        self.pages: dict[str, str] = {}  # page_id -> team, for pages actually recorded
        self.oncall_teams: set[str] = set()  # teams whose on-call the agent looked up
        self.budgets: set[str] = set()  # services whose error budget the agent computed

    def record(self, tool_name: str, arguments: Any, result: dict[str, Any]) -> None:
        """Call only for successful results; a failed call produced no evidence."""
        args = arguments if isinstance(arguments, dict) else {}
        if tool_name in {"search_runbooks", "search_postmortems", "find_similar_incidents"}:
            for row in result.get("results", []):
                if "doc_id" in row:
                    self.documents[row["doc_id"]] = row.get("doc_type", "")
        elif tool_name == "get_deploy_history":
            self.deploys.update(d["deploy_id"] for d in result.get("deploys", []) if "deploy_id" in d)
        elif tool_name == "page_oncall":
            if "page_id" in result:
                self.pages[result["page_id"]] = result.get("team", "")
        elif tool_name == "get_oncall":
            self.oncall_teams.update(v for v in (result.get("team"), result.get("rotation")) if v)
        elif tool_name == "compute_error_budget":
            if result.get("service"):
                self.budgets.add(result["service"])
        elif tool_name == "query_metrics":
            self.metrics.add(f"{result.get('service')}/{result.get('metric')}")
        elif tool_name in {"get_service", "get_dependencies", "get_dependents"}:
            service = result.get("service") or result.get("name") or args.get("service")
            if isinstance(service, str):
                self.services.add(service.strip().lower())
            # a dependency listing is evidence about every service it names
            self.services.update(item["name"] for item in result.get("services", []) if "name" in item)

    def has(self, kind: str, ref: str) -> bool:
        if kind == "document":
            return ref in self.documents
        if kind == "deploy":
            return ref in self.deploys
        if kind == "metric":
            return ref in self.metrics
        if kind == "catalog":
            return ref.strip().lower() in self.services
        return False
