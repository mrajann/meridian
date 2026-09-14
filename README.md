# Meridian — Incident Response Copilot

Portfolio project: an alert fires, four agents (triage, investigator, escalation,
comms) investigate it end to end using RAG over a synthetic corpus of runbooks,
postmortems, and a service dependency graph for a fictional e-commerce company.
See [`meridian-spec.md`](meridian-spec.md) for the full technical spec, corpus
design, agent design, and evaluation plan.

Built incrementally — one branch and one PR per increment, listed in the spec's
build table. Current: **increment 3** — corpus generator.

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
catalog/services/   41 hand-authored service catalog entries (YAML), one per service
data/corpus/     generated incident corpus (runbooks, postmortems, alerts, chats, catalog docs)
tests/           pytest suite, mirrors src/meridian layout
.env.example     documents every config value; copy to .env for local secrets
pyproject.toml   package metadata, dependencies, pytest config
```

## Service catalog

`meridian.catalog.load_catalog()` reads every file in `catalog/services/` into a
dict of `ServiceEntry` (see `src/meridian/catalog.py` for the schema), validating
that `depends_on` and `depended_on_by` agree with each other across the whole
catalog. `meridian.graph.DependencyGraph` traverses those edges in either
direction with configurable depth — `depth=None` (the default) walks the full
transitive closure, which is what cascade detection needs.

Note: the spec's prose calls this "~45 services," but its own per-layer table
sums to 41 named services — the catalog matches the table exactly rather than
padding to 45 with unnamed services.

## Corpus generator

`python -m meridian.corpus` (or `meridian.corpus.generate_corpus(catalog)`
directly) builds a deterministic, deliberately adversarial corpus and writes
it to `data/corpus/` as markdown files with a YAML frontmatter header. It's
two batches combined, 297 documents total, still a scaled-down stand-in for
the spec's full ~1,100-document corpus:

- **Batch 1** (`src/meridian/corpus/generator.py`, 32 docs) — hand-authored
  one document at a time: 12 runbooks, 9 postmortems, 6 alerts, 3 chat
  transcripts, 2 catalog docs. The flagship, narratively rich examples.
- **Batch 2** (`src/meridian/corpus/scale.py`, 265 docs) — template-driven:
  a fixed taxonomy of ~18 failure categories, one body template per category,
  and deterministic (no-randomness) assignment of (service, category) pairs
  to documents. 100 runbooks, 75 postmortems, 50 alerts, 25 chat transcripts,
  15 catalog docs. This is the bulk/long-tail tier, the same way a real
  corpus has a long tail of formulaic runbooks behind a handful of
  well-loved ones — matches how the spec itself describes the full corpus:
  "generated from templates."

Every adversarial case from the spec is built into both batches and asserted
by `tests/test_corpus.py` (batch 1) and `tests/test_corpus_scale.py` (batch 2
and the combined corpus) directly against the generated output, not assumed:

- near-duplicate runbook pairs where only one is correct for a given alert
  (1 pair in batch 1, 10 in batch 2)
- an alert/runbook pair with no shared key vocabulary for the same failure mode
- alerts with no matching runbook anywhere in the corpus (~10%, cross-checked
  by scanning the real runbook set rather than trusting a flag)
- postgres-primary postmortems each covering six real (graph-verified)
  dependent services, rather than six separate incidents (1 in batch 1, 2
  non-overlapping ones in batch 2)
- runbooks referencing services that no longer exist in the catalog (2 in
  batch 1, 6 more in batch 2, across 5 distinct decommissioned service names)

postgres-primary, llm-gateway, and notification-service are weighted to
account for ~40% of "incidents" (alerts + postmortems combined — runbooks are
reference material and chat transcripts discuss an incident rather than being
one, so neither counts toward the ratio) — 40.00% exactly in the combined
corpus.
