---
doc_id: runbook-baseline-recommendation-engine-quality_degradation
doc_type: runbook
title: 'recommendation-engine: quality degradation'
services:
- recommendation-engine
metadata:
  root_cause_category: quality_degradation
---

recommendation-engine is showing output quality dropping with no traditional error signal. Check llm-gateway first -- recommendation-engine depends on it directly. Check the recommendation-engine dashboard and recent deploys via ci-pipeline before assuming the fault is in recommendation-engine itself.

Likely cause: a routing or model-version change degraded output quality without tripping a health check.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting recommendation-engine -- a restart will not fix quality degradation if the underlying condition is still present.

Blast radius: Recommendations fall back to generic best-sellers. No outage.
