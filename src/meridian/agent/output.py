"""What an agent must submit, as data: the tool it calls, the pydantic model
its arguments are validated against, and the grounding check that runs after
the shape is valid.

The loop (loop.py) is generic over this. The single agent's `IncidentReport`
is one `OutputSpec`; each agent in the multi-agent pipeline has its own. The
loop's behaviour is identical for all of them: a submission is validated, then
checked against the evidence the agent actually retrieved, and a rejected one
is returned to the model to fix.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel

from meridian.agent.evidence import EvidenceLedger
from meridian.catalog import ServiceEntry

# (validated output, evidence the agent retrieved, catalog) -> problems; empty = grounded
Check = Callable[[Any, EvidenceLedger, dict[str, ServiceEntry]], list[str]]


def inline_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON Schema with `$ref`s inlined, so a tool's input_schema is one self-contained object."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def inline(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return inline(defs[node["$ref"].rsplit("/", 1)[-1]])
            return {k: inline(v) for k, v in node.items() if k != "title"}
        if isinstance(node, list):
            return [inline(v) for v in node]
        return node

    return inline(schema)


@dataclass(frozen=True)
class OutputSpec:
    tool_name: str
    description: str
    model: type[BaseModel]
    check: Check
    # Appended to the nudge and final-turn messages: a noun phrase completing "submit ..." / "use ..." for when there is nothing solid to report.
    fallback_hint: str = "outcome=insufficient_evidence"

    def tool_schema(self) -> dict[str, Any]:
        return {"name": self.tool_name, "description": self.description, "input_schema": inline_schema(self.model)}
