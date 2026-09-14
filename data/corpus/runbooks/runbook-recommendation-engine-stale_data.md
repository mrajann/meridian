---
doc_id: runbook-recommendation-engine-stale_data
doc_type: runbook
title: 'recommendation-engine: stale data'
services:
- recommendation-engine
metadata:
  root_cause_category: stale_data
---

recommendation-engine is showing results or dashboards reflecting outdated state with no errors thrown. Check llm-gateway first -- recommendation-engine depends on it directly. Check the recommendation-engine dashboard and recent deploys via ci-pipeline before assuming the fault is in recommendation-engine itself.

Likely cause: a background refresh or index job has been failing silently.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting recommendation-engine -- a restart will not fix stale data if the underlying condition is still present.

Blast radius: Recommendations fall back to generic best-sellers. No outage.
