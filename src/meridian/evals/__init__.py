"""Evaluation harnesses. Currently: retrieval quality against the corpus's
own labelled alerts (precision@k, recall@k, MRR, no-match/abstention)."""

from meridian.evals.report import render_markdown
from meridian.evals.retrieval import (
    DEFAULT_K,
    SEARCH_DEPTH,
    CaseResult,
    EvalCase,
    Metrics,
    ModeReport,
    NoMatchAnalysis,
    RetrievalEvalReport,
    ScoreStats,
    build_eval_cases,
    evaluate_mode,
    evaluate_retrieval,
)

__all__ = [
    "DEFAULT_K",
    "SEARCH_DEPTH",
    "CaseResult",
    "EvalCase",
    "Metrics",
    "ModeReport",
    "NoMatchAnalysis",
    "RetrievalEvalReport",
    "ScoreStats",
    "build_eval_cases",
    "evaluate_mode",
    "evaluate_retrieval",
    "render_markdown",
]
