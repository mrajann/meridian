# Meridian — Incident Response Copilot

Portfolio project: an alert fires, four agents (triage, investigator, escalation,
comms) investigate it end to end using RAG over a synthetic corpus of runbooks,
postmortems, and a service dependency graph for a fictional e-commerce company.
See [`meridian-spec.md`](meridian-spec.md) for the full technical spec, corpus
design, agent design, and evaluation plan.

Built incrementally — one branch and one PR per increment, listed in the spec's
build table. This is **increment 1**: repo scaffold only.

## Setup

Requires Python 3.11+.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
```

## Running tests

```bash
pytest
```

## Project layout

```
src/meridian/    application package (import as `meridian`)
tests/           pytest suite, mirrors src/meridian layout
.env.example     documents every config value; copy to .env for local secrets
pyproject.toml   package metadata, dependencies, pytest config
```
