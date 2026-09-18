---
doc_id: runbook-baseline-recommendation-engine-latency_spike
doc_type: runbook
title: 'recommendation-engine: latency spike'
services:
- recommendation-engine
metadata:
  root_cause_category: latency_spike
---

recommendation-engine is showing p99 latency above its SLO target. Check llm-gateway first -- recommendation-engine depends on it directly. Check the recommendation-engine dashboard and recent deploys via ci-pipeline before assuming the fault is in recommendation-engine itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting recommendation-engine -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Recommendations fall back to generic best-sellers. No outage.
