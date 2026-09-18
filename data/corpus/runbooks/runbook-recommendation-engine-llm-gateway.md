---
doc_id: runbook-recommendation-engine-llm-gateway
doc_type: runbook
title: 'recommendation-engine: requests to an external provider failing or timing
  out (llm-gateway root cause)'
services:
- recommendation-engine
metadata:
  root_cause_category: third_party_outage__llm-gateway
---

recommendation-engine is showing requests to an external provider failing or timing out. Check the recommendation-engine dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: llm-gateway is degraded or unavailable, so recommendation-engine's calls to it are failing or timing out.

Fix: check llm-gateway health directly before touching recommendation-engine itself.
