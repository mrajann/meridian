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
src/meridian/agent/       the single-agent loop, trace and report schema (see Single agent)
src/meridian/multiagent/  the four-agent LangGraph pipeline, handoff schemas, comparison (see Multi-agent)
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

## Single agent

`meridian.agent` is one agent with all eleven tools, driven by a hand-written
loop (`loop.py`, no framework): send messages and tool schemas, run every
`tool_use` block, send the `tool_result`s back, repeat until the model submits
a report. It needs `ANTHROPIC_API_KEY` and a built index:

```bash
python -m meridian.agent list
python -m meridian.agent run alert-cascade-feature-flags-9   # also writes reports/traces/<incident>-<run>.json
```

**Failure handling, each covered by a test:**

| Situation | What the loop does |
|---|---|
| Several `tool_use` blocks in one response | Runs all, in order; returns all results in one user message |
| Tool rejects the call (bad/missing/unknown arguments, non-object input, unknown tool) | `is_error` result with the message; the model retries |
| Tool raises an unexpected exception | `is_error` result with only the exception type; full traceback kept in the trace |
| Response cut off by `max_tokens` | Discards its tool calls (arguments may be truncated), asks for a shorter turn |
| Model stops without submitting | One nudge, then fails with `no_report` |
| Iteration cap (`--max-iterations`, default 12) | The last allowed call forces `submit_report` through `tool_choice`; if that still yields no valid report the run fails (`max_iterations` / `invalid_report`) |
| Model API error | Run fails with `api_error`; the trace survives |

**Output** is a pydantic `IncidentReport` submitted through a `submit_report`
tool whose schema is generated from the model: severity (SEV1-4), affected
services, outcome, root cause (service, category, confidence, citations),
`matching_runbook`, recommended action. `outcome="insufficient_evidence"` is a
first-class path: it must have `root_cause=null` and at least one stated
evidence gap, so "unknown" and "diagnosed" cannot be blurred. `matching_runbook`
is independent: a cause can be known with no runbook for it.

**Citations are checked, not trusted.** The loop records every document, deploy,
metric series and catalog entry the tools actually returned (`evidence.py`); a
report citing anything else, or naming a service not in the catalog, is rejected
and sent back to the model to fix.

**Trace** (`trace.py`): one `RunTrace` per run, a `TurnTrace` per model call
(agent, duration, input/output/cache tokens, stop reason, text, notes) and a
`ToolCallTrace` per tool call (arguments exactly as sent, result exactly as
shown, error kind, duration). It is plain JSON and carries `agent` on every turn
so the same structure can describe several agents later. Its schema version,
prompt hash and tool list are recorded so a behaviour change can be attributed.

The model sits behind a small `ModelClient` interface; tests and CI drive the
loop with `ScriptedClient` and make no network calls. **The loop has been
exercised only against that scripted client so far, not against the live API.**

## Multi-agent

`meridian.multiagent` runs the same incident through four agents, orchestrated
with LangGraph. Each agent is the increment 7 loop, unchanged in behaviour, run
with its own tools, prompt and output schema:

| Agent | Tools | Hands on |
|---|---|---|
| Triage | `get_service`, `get_dependencies`, `get_dependents`, `query_metrics` | `TriageHandoff`: severity, cascade, affected services, **investigation targets**, at-risk services, blast radius, plain-words customer impact |
| Investigator | `search_runbooks`, `search_postmortems`, `find_similar_incidents`, `get_deploy_history`, `query_metrics` | `Investigation`: cause with citations or `insufficient_evidence`, matching runbook, action |
| Escalation | `get_oncall`, `compute_error_budget`, `get_service`, `page_oncall` | `EscalationDecision`: `page_now` / `notify_business_hours` / `no_action`, team, page id |
| Comms | none | `CustomerUpdate`: impact first, confirmed vs suspected, next update time |

An agent cannot call a tool outside its list: the toolset rejects it as unknown
(tested for all 31 agent/tool pairs that aren't allowed). The Investigator is
shown Triage's `investigation_targets`, so on a cascade it is pointed at the
shared upstream rather than the alerting services.

**Handoffs are schemas, checked twice.** The loop validates each agent's output
against its pydantic model and then runs a grounding check, sending problems back
to the model: Triage's and the Investigator's citations must be things their own
tools returned; the Escalation decision must match what the pager actually
recorded (a page made must be reported, a page reported must exist, one page at
most); the customer update may contain no service names, severity labels or
document ids, and may not claim a cause the Investigator did not find. The
payload recorded for each handoff is the exact JSON the next agent is shown.

**Failure policy.** Triage fails: the run ends. Investigator fails: a
system-written `insufficient_evidence` investigation (flagged `system_fallback`)
goes on, so a SEV1 still gets paged on severity alone. Escalation or Comms fails:
a `partial` packet, and Comms still runs if only Escalation failed.

**Trace.** A `PipelineTrace` holds one `RunTrace` per agent (its own tool list,
turns, calls, tokens) plus a `HandoffTrace` for every data flow (from, to, schema,
source, valid, payload) and the graph path. It exposes the same totals as a
single-agent `RunTrace`.

**Comparing the two.** The increment 7 agent is untouched and still the default:

```bash
python -m meridian.agent run <incident>                       # single agent
python -m meridian.agent run <incident> --architecture multi  # four agents
python -m meridian.agent compare --sample 5                   # both, same incidents -> reports/architecture_comparison.json
```

Both produce a `RunSummary` with the same fields (severity, root cause, outcome,
matching runbook, pages made, model calls, tokens, latency) and a quick score
against the synthetic ground truth. That score is scaffolding for increment 9's
eval harness, not a replacement for it.

**Caveats.** Like the single agent, this has run only against a scripted model,
never the live API. The orchestration is a straight line with one conditional
edge (Triage failure); each agent needs the previous one's output, so LangGraph
adds structure here more than parallelism. The no-jargon check catches exact
identifiers only, not paraphrases such as "checkout api".
