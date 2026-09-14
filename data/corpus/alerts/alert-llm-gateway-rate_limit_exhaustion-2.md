---
doc_id: alert-llm-gateway-rate_limit_exhaustion-2
doc_type: alert
title: 'llm-gateway: requests queueing or being rejected outright (recurrence #2)'
services:
- llm-gateway
metadata:
  root_cause_service: llm-gateway
  root_cause_category: rate_limit_exhaustion
  correct_runbook: runbook-llm-gateway-rate-limit
  has_matching_runbook: true
  fragile_service: llm-gateway
---

llm-gateway: requests queueing or being rejected outright. Onset was within the last monitoring window -- investigate before it breaches SLO further.
