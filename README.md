# Meridian — Incident Response Copilot

Portfolio project: an alert fires, four agents (triage, investigator, escalation,
comms) investigate it end to end using RAG over a synthetic corpus of runbooks,
postmortems, and a service dependency graph for a fictional e-commerce company.
See [`meridian-spec.md`](meridian-spec.md) for the full technical spec, corpus
design, agent design, and evaluation plan.

Built incrementally — one branch and one PR per increment, listed in the spec's
build table. Current: **increment 5** — retrieval layer and retrieval evaluation.

## Setup

Requires Python 3.11+.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev,local-embeddings]"   # local-embeddings pulls in torch; omit it to run on the
                                           # dependency-free hashing embedder (EMBEDDING_BACKEND=hashing)
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
python -m meridian.indexing build          # chunk, embed, and index the corpus (~20s, first run downloads the model)
python -m meridian.evals retrieval          # run the retrieval eval, writes reports/retrieval_eval.md
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
data/chroma/     persisted vector index (gitignored; rebuilt by `python -m meridian.indexing build`)
reports/         generated eval reports (committed -- see Retrieval evaluation below)
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
directly) builds a deterministic corpus and writes it to `data/corpus/` as
markdown files with a YAML frontmatter header — 474 documents, a scaled-down
stand-in for the spec's full ~1,100-document corpus. It's built in two layers:

- **Adversarial** (`src/meridian/corpus/adversarial.py`) — each of the five
  adversarial cases from spec section 3 has its own generator function
  taking an explicit target count, so hitting a real evaluable volume per
  case is a generation parameter, not something bulk generation happens to
  reproduce (or doesn't). This is the layer the counts below describe.
- **Baseline** (`src/meridian/corpus/baseline.py`) — template-driven
  reference material filling out broad coverage across all 41 services,
  built around whatever the adversarial layer didn't already claim.

Every adversarial case is asserted by `tests/test_corpus_adversarial.py`
directly against the generated output — a minimum-count floor per category
plus a correctness check, so both the volume and the substance of each case
are regression-guarded:

| Case | Count | Verified by |
|---|---|---|
| Near-duplicate runbook pairs | 28 | textual similarity > 0.55, differing root cause |
| Vocabulary-mismatch cases | 28 | zero shared key phrase (`src/meridian/corpus/synonyms.py`, 28 alert/runbook phrasing pairs) |
| Alerts with no matching runbook | 15 | scanned against the *entire* generated runbook set, not just a flag |
| Cascading-failure sets | 13 | each covers 6 real (`DependencyGraph`-verified) dependents of a hub service, non-overlapping within that hub |
| Stale runbooks | 10 | across 5 decommissioned service names, all confirmed absent from `load_catalog()` |

postgres-primary, llm-gateway, and notification-service are weighted to
account for ~40% of "incidents" (alerts + postmortems combined — runbooks are
reference material and chat transcripts discuss an incident rather than being
one, so neither counts toward the ratio) — 40.1% in the generated corpus.
Cascades are the exception: only postgres-primary among the three fragile
services has enough real dependents (24) to support 6-service cascades, so
the other 9 cascade sets are built on different well-connected hubs
(redis-cache, postgres-replica, secrets-manager, feature-flags,
inventory-service, pricing-engine, kafka-broker) rather than forced onto
llm-gateway or notification-service, which don't have the dependents to
support one honestly.

## Indexing

`python -m meridian.indexing build` chunks the corpus, embeds each chunk, and
writes a persisted ChromaDB index (`python -m meridian.indexing query "..."
--type runbook --tier 1` searches it). The code is in `src/meridian/indexing/`:
`chunking.py` (per-type strategies), `embeddings.py` (the swappable `Embedder`
interface), `store.py` (Chroma wrapper), `pipeline.py` (ties them together).

**Chunking is per document type, sized from the embedder.** The chunk budget is
75% of the embedder's input limit (192 of 256 tokens for the default
all-MiniLM-L6-v2), counted with the model's own tokenizer, so nothing is
silently truncated and a model with a bigger window re-chunks automatically.

| Type | Strategy | Overlap |
|---|---|---|
| runbook | whole paragraphs packed up to the budget; a numbered procedure is never cut mid-step | none |
| postmortem | one chunk per named section (Summary / Timeline / Root cause / Remediation / Action items); small sections are not merged | none |
| chat transcript | sliding window of whole turns | 2 turns |
| alert, catalog entry | atomic | none |
| any oversize paragraph | sentence windows | 1 sentence |

Overlap is used only where a boundary is arbitrary. Section, step and
paragraph boundaries are semantic seams, so overlapping there would only
duplicate text and put near-identical hits in top-k. Context is carried by a
header (type, title, services) embedded with each chunk but not stored as its
content.

Every document in the current corpus fits in 153 tokens, so size-based
splitting never triggers on it; the oversize paths are covered by tests on
synthetic long documents. The result is 680 chunks from 474 documents (the
spec's "6-8k" estimate assumed much longer documents).

**Filterable metadata:** `doc_type`, `service` (primary), `services` (all, matched
with `$contains`), `tier` (of the primary service, as a string: `"1"`, `"2"`,
`"3"`, `"external"`, or `"unknown"` for a service missing from the catalog),
plus `doc_id`, `section`, `chunk_index`. Ground-truth labels
(`correct_runbook`, `root_cause_category`, ...) are deliberately never indexed,
so a retriever can't filter on the answer.

**Swapping the embedder:** anything satisfying `Embedder` works. The index
records which embedder built it and refuses to be queried by a different one
(vectors from different models are not comparable, and the failure would
otherwise be silent). `HashingEmbedder` is a dependency-free lexical baseline
used by CI; the real-model tests skip when `sentence-transformers` isn't
installed.

## Retrieval

`src/meridian/retrieval/` wraps the Chroma index (`meridian.indexing`) behind
a `Retriever` with configurable `k`, metadata filtering (`meridian.indexing.
store.build_filter`), and three search modes:

- `"vector"` — the semantic similarity search from increment 4, as-is.
- `"keyword"` — Okapi BM25 (`retrieval/keyword.py`, pure Python, no new
  dependency) over the exact same chunks, fetched from the index itself
  (`VectorIndex.all_chunks()`) rather than re-derived, so it can never drift
  out of sync with what's actually indexed. Reconstructs each chunk's
  title/services context from metadata, since only the bare chunk text is
  stored as Chroma's `documents` field — otherwise keyword search would be
  working from less context than vector search gets from the embedded header.
- `"hybrid"` — vector and keyword ranked lists combined by Reciprocal Rank
  Fusion (rank-based, so it needs no normalization across BM25's and cosine
  similarity's very different scales).

## Retrieval evaluation

`python -m meridian.evals retrieval` runs precision@5/recall@5/MRR for all
three modes against the corpus's own alerts, which already carry ground truth
(`correct_runbook`, `has_matching_runbook`, `adversarial_case`) from how the
corpus is generated — increment 5 needed no separate labelled eval set. Every
alert has at most one relevant runbook, so precision@k/recall@k/MRR take the
single-relevant-document form (see `src/meridian/evals/retrieval.py`).
Results are broken down **by adversarial category**, not just overall, since
the aggregate hides exactly the cases that matter — see
[`reports/retrieval_eval.md`](reports/retrieval_eval.md) for the real
(all-MiniLM-L6-v2) numbers. Highlights as of that report:

- **Near-duplicate runbook pairs are the easiest case** (recall@5 = 1.000):
  the two runbooks in a pair are near-identical, so whichever the query
  resembles at all, it resembles strongly.
- **Vocabulary mismatch is the intended hard case, and it is measurably
  harder than baseline** — but not dramatically, because the alert and its
  runbook still share the service name and template wording; only the
  failure-mode phrase itself differs.
- **Cascading failures are the hardest category by a wide margin** (recall@5
  ≈ 0.46, roughly half of every other category, on every retrieval mode).
  This isn't a bug: a cascade alert's text names the *affected* services,
  while its root-cause runbook is worded entirely around the *hub* service —
  a single-query similarity search naturally retrieves runbooks about the
  named services instead. Confirms the spec's premise that cascade
  attribution needs more than retrieval alone (the dependency graph from
  increment 2, reasoned over by an agent).

**No-match / abstention:** for alerts with no correct runbook, does the
top-1 similarity score alone come out low enough to abstain on? Not cleanly —
matched and unmatched top-1 scores overlap by roughly 0.2 (vector mode), so a
single fixed threshold would misclassify cases in that band either way.
Abstention needs more than top-1 score (e.g. the gap to the #2 hit, or an LLM
judging the retrieved runbook against the alert) — left for a later increment.

**In CI:** `tests/test_evals_retrieval.py` runs the full eval on the
dependency-free `HashingEmbedder` and asserts regression-guard floors (not
quality targets — e.g. cascading failure has no floor, since scoring badly
there is the expected, documented finding). The workflow also builds the
index and runs `python -m meridian.evals retrieval` as its own CI step
(hashing backend, no torch), uploading the report as a build artifact. The
real semantic numbers in `reports/retrieval_eval.md` are generated locally
with the real model and committed, the same pattern as the corpus itself.
