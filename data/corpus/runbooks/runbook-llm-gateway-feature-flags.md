---
doc_id: runbook-llm-gateway-feature-flags
doc_type: runbook
title: 'llm-gateway: requests queueing or being rejected outright (feature-flags root
  cause)'
services:
- llm-gateway
metadata:
  root_cause_category: rate_limit_exhaustion__feature-flags
---

llm-gateway is showing requests queueing or being rejected outright. Check the llm-gateway dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: feature-flags is degraded or unavailable, so llm-gateway's calls to it are failing or timing out.

Fix: check feature-flags health directly before touching llm-gateway itself.
