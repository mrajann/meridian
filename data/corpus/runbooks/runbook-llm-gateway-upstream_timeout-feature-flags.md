---
doc_id: runbook-llm-gateway-upstream_timeout-feature-flags
doc_type: runbook
title: 'llm-gateway: upstream timeout (feature-flags root cause)'
services:
- llm-gateway
metadata:
  root_cause_category: upstream_timeout__feature-flags
---

llm-gateway is showing elevated latency or errors tracing to one specific upstream call. Check the llm-gateway dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: a feature-flags rollout changed model routing to a provider region that is currently degraded.

Fix: roll back the routing flag in feature-flags to the previous known-good region.
