"""Run the agent(s) on incidents.

    python -m meridian.agent list
    python -m meridian.agent run alert-cascade-feature-flags-9                       # single agent (increment 7)
    python -m meridian.agent run alert-cascade-feature-flags-9 --architecture multi  # four agents (increment 8)
    python -m meridian.agent compare --sample 5                                      # both, on the same incidents

Needs ANTHROPIC_API_KEY (see .env.example) and a built index
(python -m meridian.indexing build).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from meridian.agent.client import AnthropicClient
from meridian.agent.loop import AgentConfig
from meridian.agent.session import IncidentSession, open_incidents
from meridian.config import settings

ARCHITECTURES = ("single", "multi")


def _list(args: argparse.Namespace) -> None:
    for incident_id in sorted(open_incidents(settings)):
        print(incident_id)


def _client(args: argparse.Namespace) -> AnthropicClient:
    return AnthropicClient(settings.anthropic_api_key, args.model or settings.anthropic_model)


def _print_trace(trace) -> None:
    runs = getattr(trace, "agents", None) or [trace]
    for run in runs:
        for turn in run.turns:
            calls = ", ".join(f"{c.name}{'!' if c.is_error else ''}" for c in turn.tool_calls) or "-"
            print(
                f"{run.agent:<12} turn {turn.index}: {turn.duration_ms:7.0f}ms  "
                f"in={turn.input_tokens:<6} out={turn.output_tokens:<5} {calls}"
            )
    reason = getattr(trace, "failure_reason", None)
    print(
        f"\n{trace.status}" + (f" ({reason})" if reason else "") + f": {trace.model_calls} model calls, {trace.tool_calls} tool calls "
        f"({trace.tool_errors} errors), {trace.input_tokens} in / {trace.output_tokens} out tokens, "
        f"{trace.duration_ms / 1000:.1f}s"
    )


def _run(args: argparse.Namespace) -> None:
    from meridian.multiagent.compare import run_architecture

    sessions = open_incidents(settings)
    if args.incident not in sessions:
        raise SystemExit(f"unknown incident '{args.incident}'; list them with: python -m meridian.agent list")
    session = sessions[args.incident]
    summary, trace = run_architecture(args.architecture, session, _client(args), max_iterations=args.max_iterations)

    _print_trace(trace)
    if summary.failure:
        print(f"failure: {summary.failure}")
    print(json.dumps({k: v for k, v in summary.__dict__.items() if v not in (None, [])}, indent=2))
    pages = session.ctx.pager.records
    if pages:
        print(f"\nsimulated pages: {[(p.rotation, p.severity) for p in pages]}")

    args.trace_dir.mkdir(parents=True, exist_ok=True)
    path = args.trace_dir / f"{args.incident}-{args.architecture}-{trace.run_id}.json"
    path.write_text(trace.model_dump_json(indent=2))
    print(f"trace: {path}")
    raise SystemExit(0 if summary.status in ("completed", "partial") else 1)


def _pick(sessions: dict[str, IncidentSession], args: argparse.Namespace) -> list[str]:
    if args.incidents:
        unknown = [i for i in args.incidents if i not in sessions]
        if unknown:
            raise SystemExit(f"unknown incident(s) {unknown}")
        return args.incidents
    ids = sorted(sessions)
    step = max(1, len(ids) // args.sample)
    return ids[::step][: args.sample]  # evenly spread over the sorted ids, so the same N every time


def _compare(args: argparse.Namespace) -> None:
    from meridian.multiagent.compare import as_dict, run_architecture, score

    sessions = open_incidents(settings)
    client = _client(args)
    chosen = _pick(sessions, args)
    rows: list[dict] = []
    for incident_id in chosen:
        for architecture in ARCHITECTURES:
            # a fresh session per run: each has its own telemetry and pager
            session = sessions[incident_id].fresh()
            summary, trace = run_architecture(architecture, session, client, max_iterations=args.max_iterations)
            rows.append(as_dict(summary, score(summary, session)))
            args.trace_dir.mkdir(parents=True, exist_ok=True)
            (args.trace_dir / f"{incident_id}-{architecture}-{trace.run_id}.json").write_text(trace.model_dump_json(indent=2))
            print(f"{incident_id:<48} {architecture:<6} {summary.status:<9} cause={summary.root_cause_service} "
                  f"tokens={summary.input_tokens + summary.output_tokens} {summary.duration_ms / 1000:.1f}s", flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, indent=2))
    print(f"\n{len(rows)} runs written to {args.out}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m meridian.agent", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list incident ids").set_defaults(func=_list)

    def common(p):
        p.add_argument("--model", default=None, help="override ANTHROPIC_MODEL")
        p.add_argument("--max-iterations", type=int, default=None, help=f"model-call cap per agent (default {AgentConfig.max_iterations} single, per-agent for multi)")
        p.add_argument("--trace-dir", type=Path, default=Path("reports/traces"))

    run = sub.add_parser("run", help="investigate one incident")
    run.add_argument("incident")
    run.add_argument("--architecture", choices=ARCHITECTURES, default="single")
    common(run)
    run.set_defaults(func=_run)

    compare = sub.add_parser("compare", help="run both architectures on the same incidents")
    compare.add_argument("--incidents", nargs="+", default=None)
    compare.add_argument("--sample", type=int, default=5, help="how many incidents when --incidents is not given")
    compare.add_argument("--out", type=Path, default=Path("reports/architecture_comparison.json"))
    common(compare)
    compare.set_defaults(func=_compare)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
