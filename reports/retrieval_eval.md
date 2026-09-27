# Retrieval evaluation

Embedder: `sentence-transformers/all-MiniLM-L6-v2` | generated 2026-09-27 08:05 UTC

Ground truth comes from the corpus's own alert metadata (`correct_runbook`, `has_matching_runbook`, `adversarial_case`) -- see `src/meridian/corpus/adversarial.py` and `src/meridian/evals/retrieval.py`. Hit@1/recall/MRR are computed only over alerts that have a correct runbook; alerts with none are covered by the no-match analysis in each mode's section instead. Hit@1 (not precision@k) is the top-of-ranking metric: with exactly one relevant document per query, precision@k is capped at 1/k regardless of retrieval quality, which makes every mode look like it's failing when the ceiling is the metric, not the retriever.

## Mode comparison (overall, matched incidents)

| Mode | n | Hit@1 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| `vector` | 109 | 0.495 | 0.817 | 0.650 |
| `keyword` | 109 | 0.394 | 0.679 | 0.513 |
| `hybrid` | 109 | 0.505 | 0.826 | 0.658 |


### Mode: `vector`

Matched incidents only (has_matching_runbook=True); k=5, search depth=10.

| Category | n | Hit@1 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| **overall** | 109 | 0.495 | 0.817 | 0.650 |
| baseline (no adversarial case) | 40 | 0.700 | 0.775 | 0.757 |
| cascading failure | 13 | 0.154 | 0.462 | 0.308 |
| near-duplicate runbook pair | 28 | 0.357 | 1.000 | 0.667 |
| vocabulary mismatch | 28 | 0.500 | 0.857 | 0.638 |

Weakest category: **cascading failure** (Hit@1=0.154, n=13).

#### No-match / abstention analysis

Top-1 similarity score of the best runbook hit, matched incidents vs. incidents with no correct runbook:

| Group | n | mean | median | min | max |
|---|---:|---:|---:|---:|---:|
| has matching runbook | 109 | 0.655 | 0.660 | 0.470 | 0.788 |
| **no** matching runbook | 15 | 0.608 | 0.631 | 0.500 | 0.682 |

**Not cleanly separable**: no-match top scores go as high as 0.682, above the lowest matched top score (0.470) -- an overlap of 0.212. A single score threshold will misclassify some cases in that band either way; abstention needs more than top-1 score alone (e.g. the score gap to the #2 hit, or an LLM judging the retrieved runbook against the alert).

#### Stale-runbook contamination

Stale runbooks (referencing a decommissioned service) are never the correct answer to any alert -- the question is whether they leak into results for real incidents anyway. **4/124** incidents (3.2%) have a stale runbook in their top-5 runbook results.

Examples (incident → stale runbook surfaced):
- `alert-baseline-checkout-api-upstream_timeout` → `runbook-stale-checkout-monolith-v1`
- `alert-near-dup-catalog-service` → `runbook-stale-warehouse-mainframe-v1`
- `alert-near-dup-warehouse-api` → `runbook-stale-warehouse-mainframe-v1`
- `alert-no-match-checkout-api-5xx_errors` → `runbook-stale-checkout-monolith-v1`


### Mode: `keyword`

Matched incidents only (has_matching_runbook=True); k=5, search depth=10.

| Category | n | Hit@1 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| **overall** | 109 | 0.394 | 0.679 | 0.513 |
| baseline (no adversarial case) | 40 | 0.425 | 0.600 | 0.477 |
| cascading failure | 13 | 0.308 | 0.615 | 0.454 |
| near-duplicate runbook pair | 28 | 0.714 | 1.000 | 0.857 |
| vocabulary mismatch | 28 | 0.071 | 0.500 | 0.249 |

Weakest category: **vocabulary mismatch** (Hit@1=0.071, n=28).

#### No-match / abstention analysis

Top-1 similarity score of the best runbook hit, matched incidents vs. incidents with no correct runbook:

| Group | n | mean | median | min | max |
|---|---:|---:|---:|---:|---:|
| has matching runbook | 109 | 22.613 | 24.129 | 7.057 | 43.020 |
| **no** matching runbook | 15 | 23.397 | 22.401 | 16.292 | 35.141 |

**Not cleanly separable**: no-match top scores go as high as 35.141, above the lowest matched top score (7.057) -- an overlap of 28.084. A single score threshold will misclassify some cases in that band either way; abstention needs more than top-1 score alone (e.g. the score gap to the #2 hit, or an LLM judging the retrieved runbook against the alert).

#### Stale-runbook contamination

Stale runbooks (referencing a decommissioned service) are never the correct answer to any alert -- the question is whether they leak into results for real incidents anyway. **0/124** incidents (0.0%) have a stale runbook in their top-5 runbook results.


### Mode: `hybrid`

Matched incidents only (has_matching_runbook=True); k=5, search depth=10.

| Category | n | Hit@1 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| **overall** | 109 | 0.505 | 0.826 | 0.658 |
| baseline (no adversarial case) | 40 | 0.675 | 0.775 | 0.739 |
| cascading failure | 13 | 0.385 | 0.538 | 0.459 |
| near-duplicate runbook pair | 28 | 0.393 | 1.000 | 0.690 |
| vocabulary mismatch | 28 | 0.429 | 0.857 | 0.601 |

Weakest category: **cascading failure** (Hit@1=0.385, n=13).

#### No-match / abstention analysis

Top-1 similarity score of the best runbook hit, matched incidents vs. incidents with no correct runbook:

| Group | n | mean | median | min | max |
|---|---:|---:|---:|---:|---:|
| has matching runbook | 109 | 3.806 | 3.967 | 3.000 | 4.000 |
| **no** matching runbook | 15 | 3.613 | 3.638 | 3.000 | 4.000 |

**Not cleanly separable**: no-match top scores go as high as 4.000, above the lowest matched top score (3.000) -- an overlap of 1.000. A single score threshold will misclassify some cases in that band either way; abstention needs more than top-1 score alone (e.g. the score gap to the #2 hit, or an LLM judging the retrieved runbook against the alert).

#### Stale-runbook contamination

Stale runbooks (referencing a decommissioned service) are never the correct answer to any alert -- the question is whether they leak into results for real incidents anyway. **3/124** incidents (2.4%) have a stale runbook in their top-5 runbook results.

Examples (incident → stale runbook surfaced):
- `alert-baseline-checkout-api-upstream_timeout` → `runbook-stale-checkout-monolith-v1`
- `alert-near-dup-warehouse-api` → `runbook-stale-warehouse-mainframe-v1`
- `alert-no-match-checkout-api-5xx_errors` → `runbook-stale-checkout-monolith-v1`


## Hybrid fusion: how scores are combined and weighted

Two fusion algorithms, each tried at a couple of vector:keyword weightings (`src/meridian/retrieval/retriever.py`):

- **rrf** -- Reciprocal Rank Fusion: `score = vector_weight / (60 + rank_v) + keyword_weight / (60 + rank_k)`. Only sees rank, not how confident either side is, so at RRF's usual damping constant, reweighting barely moves the fused order.
- **weighted_sum** -- each side's raw scores are min-max normalized to [0, 1] over its own candidate pool, then combined as `vector_weight * norm_v + keyword_weight * norm_k`. This lets a confident #1 actually outweigh a weak one, at the cost of the normalization being pool-dependent rather than a stable unit like RRF's rank.

| Fusion | n | Hit@1 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| rrf, 1:1 (unweighted) | 109 | 0.431 | 0.780 | 0.591 |
| weighted_sum, 1:1 | 109 | 0.450 | 0.798 | 0.601 |
| weighted_sum, 3:1 (current default) | 109 | 0.505 | 0.826 | 0.658 |

The unweighted 1:1 RRF that hybrid originally used underperforms pure vector search (see the mode comparison above) because keyword is consistently the weaker retriever here -- an even blend drags a strong vector ranking down by mixing in a weaker one. weighted_sum at 3:1 is the current default: it beats pure vector on every metric, because it still picks up keyword's genuinely complementary wins (BM25 clearly wins on near-duplicate pairs specifically, where the deciding signal is a literal named entity -- "postgres-primary" vs. "redis-cache" -- not a paraphrase) while vector's already-good ranking dominates the rest.
