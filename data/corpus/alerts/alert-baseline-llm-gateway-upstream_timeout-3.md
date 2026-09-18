---
doc_id: alert-baseline-llm-gateway-upstream_timeout-3
doc_type: alert
title: 'llm-gateway: elevated latency or errors tracing to one specific upstream call
  (recurrence #3)'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: upstream_timeout
  correct_runbook: runbook-baseline-llm-gateway-upstream_timeout
  has_matching_runbook: true
  fragile_service: llm-gateway
---

llm-gateway: elevated latency or errors tracing to one specific upstream call. Onset was within the last monitoring window -- investigate before it breaches SLO further.
