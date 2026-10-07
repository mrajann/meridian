# Meridian — Incident Response Copilot

Portfolio project: an alert fires, four agents (triage, investigator, escalation,
comms) investigate it end to end using RAG over a synthetic corpus of runbooks,
postmortems, and a service dependency graph for a fictional e-commerce company.
See [`meridian-spec.md`](meridian-spec.md) for the full technical spec, corpus
design, agent design, and evaluation plan.

Built incrementally — one branch and one PR per increment, listed in the spec's
build table. Current: **increment 6** — the tool layer.

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
src/meridian/tools/       the eleven agent tools + schema generation (see Tool layer)
src/meridian/telemetry/   synthetic metrics and deploy records the tools query
src/meridian/slo.py       error-budget / burn-rate math
src/meridian/oncall.py    synthetic on-call rotations and the simulated pager
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

`python -m meridian.evals retrieval` runs Hit@1/recall@5/MRR for all three
modes against the corpus's own alerts, which already carry ground truth
(`correct_runbook`, `has_matching_runbook`, `adversarial_case`) from how the
corpus is generated — increment 5 needed no separate labelled eval set. Every
alert has at most one relevant runbook, so recall@k/MRR take the
single-relevant-document form (see `src/meridian/evals/retrieval.py`).

**Hit@1, not precision@k, is the top-of-ranking metric.** With exactly one
relevant document per query, precision@k is capped at 1/k no matter how good
retrieval is — it made every mode look like it was failing when the ceiling
was the metric, not the retriever.

Results are broken down **by adversarial category**, not just overall, since
the aggregate hides exactly the cases that matter — see
[`reports/retrieval_eval.md`](reports/retrieval_eval.md) for the real
(all-MiniLM-L6-v2) numbers, regenerated on every run including a live
[hybrid fusion comparison](#hybrid-fusion). Highlights as of that report:

- **Near-duplicate runbook pairs: recall@5 = 1.000, but Hit@1 is only ~0.4
  under vector search** — the pair is deliberately near-identical, so both
  runbooks land in the top 5 regardless of which one ranks first, and
  disambiguating *which one* comes down to a single named entity (the blamed
  dependency), which is exactly BM25's strength: keyword search alone hits
  Hit@1 ≈ 0.71 here, its best category by far.
- **Vocabulary mismatch is a genuine semantic-only test.** A lexical
  retriever (keyword search, or the CI-only `HashingEmbedder` standing in for
  "vector") scores near zero Hit@1 here by design — `tests/test_evals_
  retrieval.py::test_vocabulary_mismatch_defeats_a_purely_lexical_retriever`
  guards this directly. This wasn't originally true: the alert and runbook
  bodies shared an incidental boilerplate word ("this") beyond the service
  name, letting keyword search partially cheat; removing it dropped
  keyword's Hit@1 on this category to near zero. The real model still solves
  about half of these cases outright (`test_real_model_beats_lexical_
  retrieval_on_vocabulary_mismatch` in `test_embeddings.py`).
- **Cascading failures are the hardest category by a wide margin** (Hit@1 ≈
  0.15–0.39 depending on mode, well below every other category). Not a bug:
  a cascade alert's text names the *affected* services, while its root-cause
  runbook is worded entirely around the *hub* service — a single-query
  similarity search naturally retrieves runbooks about the named services
  instead. Confirms the spec's premise that cascade attribution needs more
  than retrieval alone (the dependency graph from increment 2, reasoned over
  by an agent).

**Abstention.** For alerts with no correct runbook, can an agent tell "I found
nothing" from "I found it" using only what retrieval returns? Judged on **raw
vector cosine similarity**, regardless of retrieval mode, because it is the
only absolute-scale score available: BM25 is unbounded and depends on query
length and corpus statistics, and the hybrid `weighted_sum` score is
min-max-normalized per query, so its best hit lands near the maximum however
weak the match (neither is comparable across queries, which a threshold
needs). Two signals, each reported as matched-vs-unmatched mean/std dev, a
threshold-free AUC, and the best single threshold:

- **Top-1 cosine** — a weak signal, not a usable one. The groups overlap
  (AUC ≈ 0.67); the best threshold abstains correctly on every no-match case
  but also abstains on over half of the incidents that *do* have a runbook.
- **Gap between the top two hits** — no better than a coin flip (AUC ≈ 0.52),
  contrary to the hypothesis that a weak lead marks "nothing distinctive found".

Only 15 incidents have no correct runbook, so these are rough estimates, and
the best-threshold figures are chosen on the same cases they're scored on
(optimistic). Abstention needs more than a score cutoff — e.g. an LLM judging
the retrieved runbook against the alert — left for a later increment. Exact,
regenerated figures are in `reports/retrieval_eval.md`.

**Stale-runbook contamination:** stale runbooks are never the correct answer
to anything, so the meaningful question is whether they leak into results for
real incidents anyway. A handful do under vector search (e.g. a
`checkout-api` alert surfacing the decommissioned `checkout-monolith-v1`
runbook) — reported per mode, not just asserted absent.

### Hybrid fusion

`meridian.retrieval.Retriever` supports two fusion algorithms for combining
vector and keyword rankings, both weighted (`vector_weight`/`keyword_weight`):

- **`rrf`** — Reciprocal Rank Fusion, rank-only. At RRF's usual damping
  constant, reweighting barely moves the fused order — it doesn't distinguish
  a confident #1 from a marginal one.
- **`weighted_sum`** (default) — each side's raw scores are min-max
  normalized to `[0, 1]` over its own candidate pool, then combined linearly.
  A confident #1 can now actually outweigh a weak one.

The original hybrid mode used unweighted 1:1 RRF, which underperformed pure
vector search — an even blend drags a strong vector ranking down by mixing in
a weaker one, since keyword is consistently the weaker retriever here.
`weighted_sum` at **3:1 (vector:keyword)** beats pure vector on every metric
instead of merely approximating it, because it still picks up keyword's
genuinely complementary wins (near-duplicate pairs) while vector's
already-good ranking dominates everywhere else. The comparison across both
algorithms and a few weightings is regenerated in every report — see
`reports/retrieval_eval.md`'s "Hybrid fusion" section for current numbers
rather than a snapshot here that can drift out of sync.

**In CI:** `tests/test_evals_retrieval.py` runs the full eval on the
dependency-free `HashingEmbedder` and asserts regression-guard floors (not
quality targets — e.g. cascading failure has no floor, since scoring badly
there is the expected, documented finding, and vocabulary mismatch has a
*ceiling* on lexical retrievers instead of a floor). The workflow also builds
the index and runs `python -m meridian.evals retrieval` as its own CI step
(hashing backend, no torch), uploading the report as a build artifact. The
real semantic numbers in `reports/retrieval_eval.md` are generated locally
with the real model and committed, the same pattern as the corpus itself.

## Tool layer

`meridian.tools` implements the eleven tools from the spec as plain Python
functions: `search_runbooks`, `search_postmortems`, `find_similar_incidents`,
`get_service`, `get_dependencies`, `get_dependents`, `query_metrics`,
`get_deploy_history`, `compute_error_budget`, `get_oncall`, `page_oncall`.

```python
toolset = Toolset(build_context(catalog, retriever, scenario))
toolset.schemas()                        # tools=[...] for the Anthropic Messages API
toolset.run_tool_use(tool_use_block)     # -> tool_result block (is_error set on a ToolError)
toolset.get_dependents("postgres-primary", depth=3)   # or call them as ordinary functions
```

**Schemas are generated, not written.** `tools/schema.py` builds each tool's
JSON Schema from its signature (types, `Literal` enums, `Annotated[..,
Field(ge=, le=)]` bounds, defaults) and takes descriptions from the docstring.
The same machinery validates what the model sends back and reports *every*
problem in one message, so a bad call can be fixed in one retry. A tool can't
be registered with a thin description or an undocumented parameter (checked at
import), and tests assert the published schema and the runtime validator agree.

**Service and team names are normalized by their type, not by each tool.**
`ServiceName` / `TeamName` (`tools/types.py`) strip whitespace and fold case
inside the one validation step every call passes through, so a tool body only
ever sees the canonical form -- "Checkout-API" and " CHECKOUT-API " cannot
reach tool code in any other spelling. Registration enforces it: every string
parameter must declare its kind (`ServiceName`/`TeamName`, or a `Verbatim`
type such as `SearchText`), a bare `service: str` fails at import with
instructions, and a parameter named `service`/`services`/`team` can't be
declared verbatim. Tests enumerate the live registry (including any future
tool) and require mixed-case input to produce identical output.

**The docstring is the prompt.** Each says what the tool is for, when *not* to
use it, how to read the output, and the specific traps: a stale runbook
references a service `get_service` can't find; a deploy before an incident is
a lead, not an answer; a quiet metric is not proof of health.

**Retrieval tools return both scores, labelled.** The ranking is hybrid
(`weighted_sum` 3:1), whose score is min-max normalized per query and so
can't express match quality. Every result therefore also carries
`cosine_similarity` (raw vector cosine, absolute scale), and the response
carries `top1_cosine_similarity` and `gap_to_second_hit` -- the signals the
abstention analysis measured. The cosine is computed from the stored
embedding for every returned chunk, including ones only keyword search found.
The investigated incident's own alert (and, for cascades, its postmortem) is
excluded from retrieval so an agent can't look up its own answer.

**Synthetic telemetry** (`meridian.telemetry`) is deterministic -- a pure
function of (incident, service, metric, minute) -- and built from each corpus
alert's labels. Each failure category has a metric signature (a connection
pool saturating, a disk filling for 90 minutes *before* the incident, a memory
leak ramping for two hours), and downstream services show weaker, lagged
symptoms. Deliberately, `quality_degradation`, `stale_data` and `job_failure`
on services with no queue metric leave every metric untouched, and an
unrelated short latency blip appears on another service. Of 124 incidents, 29
have a deploy that genuinely caused them and 46 have a coincidental deploy
just before onset; causal and coincidental deploys draw changelog text from
overlapping pools, so neither timing nor wording gives it away. None of that
ground truth is ever returned by a tool (a test sweeps every tool across many
incidents for leaked fields).

**`compute_error_budget`** derives its burn-rate thresholds from what each
tier is meant to catch -- "spend X% of the budget within W hours" gives
`threshold = X * window_hours / W` -- rather than storing constants: a 30-day
window yields 14.4 / 6 / 3 / 1 and a 28-day window 13.44 / 5.6 / 2.8 / 0.933.
Each tier also requires a short window (1/12 of the long one) to be burning, so
alerts reset quickly after a fix. This is the multi-window formulation from
Google's SRE Workbook, which reproduces those figures; it was implemented from
that definition, not ported from SLO Studio's source.

**`page_oncall` is simulated**: it records the request in an in-memory `Pager`
and sends nothing (a test fails if it opens a socket). A repeat for the same
rotation and severity within 15 minutes is recorded but flagged as a duplicate.
