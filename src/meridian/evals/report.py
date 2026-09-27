"""Renders a RetrievalEvalReport as markdown."""

from __future__ import annotations

from meridian.evals.retrieval import BASELINE_CATEGORY, Metrics, ModeReport, RetrievalEvalReport

_CATEGORY_LABEL = {
    BASELINE_CATEGORY: "baseline (no adversarial case)",
    "near_duplicate_pair": "near-duplicate runbook pair",
    "vocabulary_mismatch": "vocabulary mismatch",
    "cascading_failure": "cascading failure",
}


def _metrics_row(label: str, m: Metrics, k: int) -> str:
    return f"| {label} | {m.n} | {m.hit_at_1:.3f} | {m.recall_at_k:.3f} | {m.mrr:.3f} |"


def _mode_section(report: ModeReport) -> str:
    lines = [
        f"### Mode: `{report.mode}`",
        "",
        f"Matched incidents only (has_matching_runbook=True); k={report.k}, "
        f"search depth={max((len(r.hits) for r in report.case_results), default=report.k)}.",
        "",
        f"| Category | n | Hit@1 | Recall@{report.k} | MRR |",
        "|---|---:|---:|---:|---:|",
        _metrics_row("**overall**", report.overall, report.k),
    ]
    for category, metrics in report.by_category.items():
        lines.append(_metrics_row(_CATEGORY_LABEL.get(category, category), metrics, report.k))

    scored = [(cat, m) for cat, m in report.by_category.items() if m.n > 0]
    if len(scored) > 1:
        worst_cat, worst = min(scored, key=lambda item: item[1].hit_at_1)
        lines += [
            "",
            f"Weakest category: **{_CATEGORY_LABEL.get(worst_cat, worst_cat)}** "
            f"(Hit@1={worst.hit_at_1:.3f}, n={worst.n}).",
        ]

    lines += ["", "#### No-match / abstention analysis", ""]
    matched, unmatched = report.no_match.matched, report.no_match.unmatched
    if matched and unmatched:
        lines += [
            "Top-1 similarity score of the best runbook hit, matched incidents vs. incidents with no correct runbook:",
            "",
            "| Group | n | mean | median | min | max |",
            "|---|---:|---:|---:|---:|---:|",
            f"| has matching runbook | {matched.n} | {matched.mean:.3f} | {matched.median:.3f} | {matched.min:.3f} | {matched.max:.3f} |",
            f"| **no** matching runbook | {unmatched.n} | {unmatched.mean:.3f} | {unmatched.median:.3f} | {unmatched.min:.3f} | {unmatched.max:.3f} |",
            "",
        ]
        if report.no_match.separable:
            lines.append(
                f"**Separable**: every no-match top score ({unmatched.max:.3f}) is below every matched top "
                f"score ({matched.min:.3f}). A fixed similarity threshold between them would let an agent "
                "abstain correctly on every case here."
            )
        else:
            overlap = report.no_match.overlap
            lines.append(
                f"**Not cleanly separable**: no-match top scores go as high as {unmatched.max:.3f}, above "
                f"the lowest matched top score ({matched.min:.3f}) -- an overlap of {overlap:.3f}. A single "
                "score threshold will misclassify some cases in that band either way; abstention needs "
                "more than top-1 score alone (e.g. the score gap to the #2 hit, or an LLM judging the "
                "retrieved runbook against the alert)."
            )
    else:
        lines.append("(not enough matched or unmatched cases with scores to compare)")

    lines += ["", "#### Stale-runbook contamination", ""]
    sc = report.stale_contamination
    lines.append(
        f"Stale runbooks (referencing a decommissioned service) are never the correct answer to any alert -- "
        f"the question is whether they leak into results for real incidents anyway. "
        f"**{sc.n_contaminated}/{sc.n_incidents}** incidents ({sc.rate:.1%}) have a stale runbook in their "
        f"top-{report.k} runbook results."
    )
    if sc.examples:
        lines.append("")
        lines.append("Examples (incident → stale runbook surfaced):")
        for incident_id, stale_id in sc.examples:
            lines.append(f"- `{incident_id}` → `{stale_id}`")

    return "\n".join(lines)


def render_markdown(report: RetrievalEvalReport) -> str:
    modes = list(report.modes.values())
    k = modes[0].k if modes else None

    lines = [
        "# Retrieval evaluation",
        "",
        f"Embedder: `{report.embedder_name}` | generated {report.generated_at}",
        "",
        "Ground truth comes from the corpus's own alert metadata "
        "(`correct_runbook`, `has_matching_runbook`, `adversarial_case`) -- see "
        "`src/meridian/corpus/adversarial.py` and `src/meridian/evals/retrieval.py`. "
        "Hit@1/recall/MRR are computed only over alerts that have a correct runbook; "
        "alerts with none are covered by the no-match analysis in each mode's section instead. "
        "Hit@1 (not precision@k) is the top-of-ranking metric: with exactly one relevant document "
        "per query, precision@k is capped at 1/k regardless of retrieval quality, which makes every "
        "mode look like it's failing when the ceiling is the metric, not the retriever.",
        "",
    ]

    if len(modes) > 1 and k is not None:
        lines += [
            "## Mode comparison (overall, matched incidents)",
            "",
            f"| Mode | n | Hit@1 | Recall@{k} | MRR |",
            "|---|---:|---:|---:|---:|",
        ]
        for m in modes:
            lines.append(_metrics_row(f"`{m.mode}`", m.overall, m.k))
        lines.append("")

    for mode_report in modes:
        lines += ["", _mode_section(mode_report), ""]

    if report.fusion_comparison:
        lines += [
            "",
            "## Hybrid fusion: how scores are combined and weighted",
            "",
            "Two fusion algorithms, each tried at a couple of vector:keyword weightings "
            "(`src/meridian/retrieval/retriever.py`):",
            "",
            "- **rrf** -- Reciprocal Rank Fusion: `score = vector_weight / (60 + rank_v) + "
            "keyword_weight / (60 + rank_k)`. Only sees rank, not how confident either side "
            "is, so at RRF's usual damping constant, reweighting barely moves the fused order.",
            "- **weighted_sum** -- each side's raw scores are min-max normalized to [0, 1] over "
            "its own candidate pool, then combined as `vector_weight * norm_v + keyword_weight * "
            "norm_k`. This lets a confident #1 actually outweigh a weak one, at the cost of the "
            "normalization being pool-dependent rather than a stable unit like RRF's rank.",
            "",
            f"| Fusion | n | Hit@1 | Recall@{k} | MRR |",
            "|---|---:|---:|---:|---:|",
        ]
        for label, metrics in report.fusion_comparison:
            lines.append(_metrics_row(label, metrics, k))
        lines += [
            "",
            "The unweighted 1:1 RRF that hybrid originally used underperforms pure vector search "
            "(see the mode comparison above) because keyword is consistently the weaker retriever "
            "here -- an even blend drags a strong vector ranking down by mixing in a weaker one. "
            "weighted_sum at 3:1 is the current default: it beats pure vector on every metric, "
            "because it still picks up keyword's genuinely complementary wins (BM25 clearly wins "
            "on near-duplicate pairs specifically, where the deciding signal is a literal named "
            "entity -- \"postgres-primary\" vs. \"redis-cache\" -- not a paraphrase) while vector's "
            "already-good ranking dominates the rest.",
            "",
        ]

    return "\n".join(lines).rstrip() + "\n"
