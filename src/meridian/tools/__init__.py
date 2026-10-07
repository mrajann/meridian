"""The eleven tools the agents call, with schemas generated from their signatures.

    toolset = Toolset(build_context(catalog, retriever, scenario))
    toolset.schemas()                     # tools=[...] for the Anthropic Messages API
    toolset.run_tool_use(tool_use_block)  # -> tool_result block
"""

# Imported in the order the spec lists the tools: registration order is the order
# the model sees them in.
from meridian.tools import retrieval_tools  # noqa: F401  search_runbooks, search_postmortems, find_similar_incidents
from meridian.tools import catalog_tools  # noqa: F401  get_service, get_dependencies, get_dependents
from meridian.tools import telemetry_tools  # noqa: F401  query_metrics, get_deploy_history
from meridian.tools import budget_tools  # noqa: F401  compute_error_budget
from meridian.tools import oncall_tools  # noqa: F401  get_oncall, page_oncall
from meridian.tools.context import ToolContext, build_context
from meridian.tools.errors import ToolDefinitionError, ToolError
from meridian.tools.registry import Tool, Toolset, registered_tools

TOOL_ORDER = [
    "search_runbooks",
    "search_postmortems",
    "find_similar_incidents",
    "get_service",
    "get_dependencies",
    "get_dependents",
    "query_metrics",
    "get_deploy_history",
    "compute_error_budget",
    "get_oncall",
    "page_oncall",
]

__all__ = [
    "TOOL_ORDER",
    "Tool",
    "ToolContext",
    "ToolDefinitionError",
    "ToolError",
    "Toolset",
    "build_context",
    "registered_tools",
]
