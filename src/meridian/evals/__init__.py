"""Evaluation harnesses. Currently: retrieval quality against the corpus's
own labelled alerts (Hit@1, recall@k, MRR, no-match/abstention, stale-runbook
contamination)."""

from meridian.evals.report import render_markdown
from meridian.evals.retrieval import (
    DEFAULT_K,
    FUSION_COMPARISON_CONFIGS,
    SEARCH_DEPTH,
    AbstentionAnalysis,
    CaseResult,
    EvalCase,
    Metrics,
    ModeReport,
    RetrievalEvalReport,
    ScoreStats,
    SignalAnalysis,
    StaleContamination,
    ThresholdResult,
    analyze_abstention,
    build_eval_cases,
    compare_fusion_strategies,
    evaluate_mode,
    evaluate_retrieval,
)

__all__ = [
    "DEFAULT_K",
    "FUSION_COMPARISON_CONFIGS",
    "SEARCH_DEPTH",
    "AbstentionAnalysis",
    "CaseResult",
    "EvalCase",
    "Metrics",
    "ModeReport",
    "RetrievalEvalReport",
    "ScoreStats",
    "SignalAnalysis",
    "StaleContamination",
    "ThresholdResult",
    "analyze_abstention",
    "build_eval_cases",
    "compare_fusion_strategies",
    "evaluate_mode",
    "evaluate_retrieval",
    "render_markdown",
]
