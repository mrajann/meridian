class ToolError(Exception):
    """A tool call failed in a way the *model* can act on.

    The message is returned to the model as the tool result, so write it for
    the model: say what was wrong, and list the valid options or the nearest
    matches rather than just "not found".
    """


class ToolDefinitionError(Exception):
    """A tool function is malformed (missing docstring parts, bad signature).
    Raised at import time so a badly documented tool can never be registered."""
