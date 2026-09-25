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
    return f"| {label} | {m.n} | {m.precision_at_k:.3f} | {m.recall_at_k:.3f} | {m.mrr:.3f} |"


def _mode_section(report: ModeReport) -> str:
    lines = [
        f"### Mode: `{report.mode}`",
        "",
        f"Matched incidents only (has_matching_runbook=True); k={report.k}, "
        f"search depth={max((len(r.hits) for r in report.case_results), default=report.k)}.",
        "",
        f"| Category | n | Precision@{report.k} | Recall@{report.k} | MRR |",
        "|---|---:|---:|---:|---:|",
        _metrics_row("**overall**", report.overall, report.k),
    ]
    for category, metrics in report.by_category.items():
        lines.append(_metrics_row(_CATEGORY_LABEL.get(category, category), metrics, report.k))

    scored = [(cat, m) for cat, m in report.by_category.items() if m.n > 0]
    if len(scored) > 1:
        worst_cat, worst = min(scored, key=lambda item: item[1].recall_at_k)
        lines += [
            "",
            f"Weakest category: **{_CATEGORY_LABEL.get(worst_cat, worst_cat)}** "
            f"(recall@{report.k}={worst.recall_at_k:.3f}, n={worst.n}).",
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
        "Precision/recall/MRR are computed only over alerts that have a correct runbook; "
        "alerts with none are covered by the no-match analysis in each mode's section instead.",
        "",
    ]

    if len(modes) > 1 and k is not None:
        lines += [
            "## Mode comparison (overall, matched incidents)",
            "",
            f"| Mode | n | Precision@{k} | Recall@{k} | MRR |",
            "|---|---:|---:|---:|---:|",
        ]
        for m in modes:
            lines.append(_metrics_row(f"`{m.mode}`", m.overall, m.k))
        lines.append("")

    for mode_report in modes:
        lines += ["", _mode_section(mode_report), ""]

    return "\n".join(lines).rstrip() + "\n"
