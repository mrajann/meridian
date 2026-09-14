---
doc_id: alert-llm-gateway-latency_spike
doc_type: alert
title: 'llm-gateway: p99 latency above its SLO target'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: latency_spike
  correct_runbook: runbook-llm-gateway-latency_spike
  has_matching_runbook: true
  fragile_service: llm-gateway
---

llm-gateway: p99 latency above its SLO target. Onset was within the last monitoring window -- investigate before it breaches SLO further.
