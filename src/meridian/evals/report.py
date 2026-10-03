"""Renders a RetrievalEvalReport as markdown."""

from __future__ import annotations

from meridian.evals.retrieval import (
    BASELINE_CATEGORY,
    AbstentionAnalysis,
    Metrics,
    ModeReport,
    RetrievalEvalReport,
    SignalAnalysis,
)

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


def _stats_row(label: str, st) -> str:
    return f"| {label} | {st.n} | {st.mean:.3f} | {st.std:.3f} | {st.median:.3f} | {st.min:.3f} | {st.max:.3f} |"


def _signal_block(signal: SignalAnalysis, unit_label: str) -> list[str]:
    lines = [
        f"| Group | n | mean {unit_label} | std dev | median | min | max |",
        "|---|---:|---:|---:|---:|---:|---:|",
        _stats_row("has matching runbook", signal.matched),
        _stats_row("**no** matching runbook", signal.unmatched),
        "",
    ]
    if signal.separable:
        lines.append(
            f"**Separable**: every no-match value ({signal.unmatched.max:.3f}) is below every matched value "
            f"({signal.matched.min:.3f}), so a threshold between them classifies every case correctly."
        )
    else:
        lines.append(
            f"**Not separable**: the two groups share a band of {signal.overlap:.3f} {unit_label} "
            f"(no-match values reach {signal.unmatched.max:.3f}; matched values go as low as "
            f"{signal.matched.min:.3f})."
        )
    t = signal.best_threshold
    lines += [
        "",
        f"AUC = {signal.auc:.3f}: the chance a randomly chosen matched incident scores higher than a randomly "
        "chosen no-match one (0.5 is a coin flip, 1.0 is perfect separation). Needs no threshold.",
        "",
        f"Best single threshold (answer if {unit_label} >= {t.threshold:.3f}, otherwise abstain): correctly "
        f"abstains on {t.abstain_correctly:.0%} of the {signal.unmatched.n} no-match incidents, but also "
        f"abstains on {t.abstain_wrongly:.0%} of the {signal.matched.n} incidents that do have a runbook "
        f"(balanced accuracy {t.balanced_accuracy:.3f}). Chosen on these same cases, so this is optimistic.",
    ]
    return lines


def _abstention_section(analysis: AbstentionAnalysis) -> str:
    matched_n = analysis.top1_cosine.matched.n if analysis.top1_cosine.matched else 0
    unmatched_n = analysis.top1_cosine.unmatched.n if analysis.top1_cosine.unmatched else 0
    lines = [
        "## Abstention analysis",
        "",
        "Could an agent tell \"I found nothing\" from \"I found it\" using only what retrieval returns? "
        f"{unmatched_n} incidents have no correct runbook anywhere in the corpus; {matched_n} do. "
        f"With only {unmatched_n} no-match cases, every figure below is a rough estimate.",
        "",
        "Both signals are computed from **raw vector cosine similarity**, regardless of retrieval mode "
        "(cosine = 1 - Chroma cosine distance; range -1 to 1). It is the only absolute-scale score available: "
        "keyword search returns raw BM25, which is unbounded and depends on query length and corpus statistics, "
        "and hybrid `weighted_sum` returns a per-query min-max-normalized score, so a query's best hit lands near "
        "the maximum however weak the match. Neither can be compared *across* queries, which is what a "
        "threshold needs, so neither is used here.",
        "",
        "### Signal 1: top-1 cosine similarity",
        "",
        *_signal_block(analysis.top1_cosine, "cosine"),
        "",
        "### Signal 2: gap between the top two hits (top-1 cosine minus top-2 cosine)",
        "",
        "A weak lead could mean \"nothing distinctive found\" even when the absolute score looks fine.",
        "",
        *_signal_block(analysis.gap, "cosine gap"),
    ]
    if analysis.n_without_second_hit:
        lines += ["", f"({analysis.n_without_second_hit} incidents retrieved fewer than two documents and are excluded from the gap signal.)"]
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
        "alerts with none are covered by the abstention analysis instead. "
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

    lines += ["", _abstention_section(report.abstention), ""]

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
