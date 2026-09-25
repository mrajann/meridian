# Retrieval evaluation

Embedder: `sentence-transformers/all-MiniLM-L6-v2` | generated 2026-09-25 06:42 UTC

Ground truth comes from the corpus's own alert metadata (`correct_runbook`, `has_matching_runbook`, `adversarial_case`) -- see `src/meridian/corpus/adversarial.py` and `src/meridian/evals/retrieval.py`. Precision/recall/MRR are computed only over alerts that have a correct runbook; alerts with none are covered by the no-match analysis in each mode's section instead.

## Mode comparison (overall, matched incidents)

| Mode | n | Precision@5 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| `vector` | 109 | 0.163 | 0.817 | 0.644 |
| `keyword` | 109 | 0.154 | 0.771 | 0.564 |
| `hybrid` | 109 | 0.161 | 0.807 | 0.638 |


### Mode: `vector`

Matched incidents only (has_matching_runbook=True); k=5, search depth=10.

| Category | n | Precision@5 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| **overall** | 109 | 0.163 | 0.817 | 0.644 |
| baseline (no adversarial case) | 40 | 0.155 | 0.775 | 0.757 |
| cascading failure | 13 | 0.092 | 0.462 | 0.308 |
| near-duplicate runbook pair | 28 | 0.200 | 1.000 | 0.667 |
| vocabulary mismatch | 28 | 0.171 | 0.857 | 0.614 |

Weakest category: **cascading failure** (recall@5=0.462, n=13).

#### No-match / abstention analysis

Top-1 similarity score of the best runbook hit, matched incidents vs. incidents with no correct runbook:

| Group | n | mean | median | min | max |
|---|---:|---:|---:|---:|---:|
| has matching runbook | 109 | 0.653 | 0.656 | 0.475 | 0.788 |
| **no** matching runbook | 15 | 0.608 | 0.631 | 0.500 | 0.682 |

**Not cleanly separable**: no-match top scores go as high as 0.682, above the lowest matched top score (0.475) -- an overlap of 0.208. A single score threshold will misclassify some cases in that band either way; abstention needs more than top-1 score alone (e.g. the score gap to the #2 hit, or an LLM judging the retrieved runbook against the alert).


### Mode: `keyword`

Matched incidents only (has_matching_runbook=True); k=5, search depth=10.

| Category | n | Precision@5 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| **overall** | 109 | 0.154 | 0.771 | 0.564 |
| baseline (no adversarial case) | 40 | 0.120 | 0.600 | 0.477 |
| cascading failure | 13 | 0.123 | 0.615 | 0.454 |
| near-duplicate runbook pair | 28 | 0.200 | 1.000 | 0.857 |
| vocabulary mismatch | 28 | 0.171 | 0.857 | 0.445 |

Weakest category: **baseline (no adversarial case)** (recall@5=0.600, n=40).

#### No-match / abstention analysis

Top-1 similarity score of the best runbook hit, matched incidents vs. incidents with no correct runbook:

| Group | n | mean | median | min | max |
|---|---:|---:|---:|---:|---:|
| has matching runbook | 109 | 22.588 | 24.188 | 6.726 | 43.020 |
| **no** matching runbook | 15 | 23.456 | 22.461 | 16.352 | 35.141 |

**Not cleanly separable**: no-match top scores go as high as 35.141, above the lowest matched top score (6.726) -- an overlap of 28.415. A single score threshold will misclassify some cases in that band either way; abstention needs more than top-1 score alone (e.g. the score gap to the #2 hit, or an LLM judging the retrieved runbook against the alert).


### Mode: `hybrid`

Matched incidents only (has_matching_runbook=True); k=5, search depth=10.

| Category | n | Precision@5 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| **overall** | 109 | 0.161 | 0.807 | 0.638 |
| baseline (no adversarial case) | 40 | 0.135 | 0.675 | 0.613 |
| cascading failure | 13 | 0.123 | 0.615 | 0.448 |
| near-duplicate runbook pair | 28 | 0.200 | 1.000 | 0.768 |
| vocabulary mismatch | 28 | 0.179 | 0.893 | 0.632 |

Weakest category: **cascading failure** (recall@5=0.615, n=13).

#### No-match / abstention analysis

Top-1 similarity score of the best runbook hit, matched incidents vs. incidents with no correct runbook:

| Group | n | mean | median | min | max |
|---|---:|---:|---:|---:|---:|
| has matching runbook | 109 | 0.032 | 0.033 | 0.030 | 0.033 |
| **no** matching runbook | 15 | 0.032 | 0.032 | 0.031 | 0.033 |

**Not cleanly separable**: no-match top scores go as high as 0.033, above the lowest matched top score (0.030) -- an overlap of 0.003. A single score threshold will misclassify some cases in that band either way; abstention needs more than top-1 score alone (e.g. the score gap to the #2 hit, or an LLM judging the retrieved runbook against the alert).
