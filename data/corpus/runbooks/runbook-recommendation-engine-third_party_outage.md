---
doc_id: runbook-recommendation-engine-third_party_outage
doc_type: runbook
title: 'recommendation-engine: third party outage'
services:
- recommendation-engine
metadata:
  root_cause_category: third_party_outage
---

recommendation-engine is showing requests to an external provider failing or timing out. Check llm-gateway first -- recommendation-engine depends on it directly. Check the recommendation-engine dashboard and recent deploys via ci-pipeline before assuming the fault is in recommendation-engine itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting recommendation-engine -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: Recommendations fall back to generic best-sellers. No outage.
