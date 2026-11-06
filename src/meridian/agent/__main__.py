"""Run the single agent on one incident.

    python -m meridian.agent list
    python -m meridian.agent run alert-cascade-feature-flags-9
    python -m meridian.agent run <incident-id> --max-iterations 8 --trace-dir reports/traces

Needs ANTHROPIC_API_KEY (see .env.example) and a built index
(python -m meridian.indexing build).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from meridian.agent.client import AnthropicClient
from meridian.agent.loop import AgentConfig, AgentLoop
from meridian.agent.prompts import incident_task
from meridian.agent.session import open_incidents
from meridian.config import settings


def _list(args: argparse.Namespace) -> None:
    for incident_id in sorted(open_incidents(settings)):
        print(incident_id)


def _run(args: argparse.Namespace) -> None:
    sessions = open_incidents(settings)
    if args.incident not in sessions:
        raise SystemExit(f"unknown incident '{args.incident}'; list them with: python -m meridian.agent list")
    session = sessions[args.incident]

    client = AnthropicClient(settings.anthropic_api_key, args.model or settings.anthropic_model)
    loop = AgentLoop(
        client, session.toolset(), session.catalog, config=AgentConfig(max_iterations=args.max_iterations)
    )
    result = loop.run(incident_task(session.alert, session.scenario.now), incident_id=args.incident)
    trace = result.trace

    for turn in trace.turns:
        calls = ", ".join(f"{c.name}{'!' if c.is_error else ''}" for c in turn.tool_calls) or "-"
        print(f"turn {turn.index}: {turn.duration_ms:7.0f}ms  in={turn.input_tokens:<6} out={turn.output_tokens:<5} {calls}")
    print(
        f"\n{trace.status}"
        + (f" ({trace.failure_reason})" if trace.failure_reason else "")
        + f": {trace.model_calls} model calls, {trace.tool_calls} tool calls ({trace.tool_errors} errors), "
        f"{trace.input_tokens} in / {trace.output_tokens} out tokens, {trace.duration_ms / 1000:.1f}s"
    )
    if result.report:
        print(result.report.model_dump_json(indent=2))
    pages = session.ctx.pager.records
    if pages:
        print(f"\nsimulated pages: {[(p.rotation, p.severity) for p in pages]}")

    args.trace_dir.mkdir(parents=True, exist_ok=True)
    path = args.trace_dir / f"{args.incident}-{trace.run_id}.json"
    path.write_text(trace.model_dump_json(indent=2))
    print(f"trace: {path}")
    raise SystemExit(0 if result.ok else 1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m meridian.agent", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list incident ids").set_defaults(func=_list)
    run = sub.add_parser("run", help="investigate one incident")
    run.add_argument("incident")
    run.add_argument("--model", default=None, help="override ANTHROPIC_MODEL")
    run.add_argument("--max-iterations", type=int, default=AgentConfig.max_iterations)
    run.add_argument("--trace-dir", type=Path, default=Path("reports/traces"))
    run.set_defaults(func=_run)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
