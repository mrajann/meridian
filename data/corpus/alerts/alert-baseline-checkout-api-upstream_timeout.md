---
doc_id: alert-baseline-checkout-api-upstream_timeout
doc_type: alert
title: 'checkout-api: elevated latency or errors tracing to one specific upstream
  call'
services:
- checkout-api
metadata:
  root_cause_service: checkout-api
  root_cause_category: upstream_timeout
  correct_runbook: runbook-vocab-checkout-api-upstream_timeout-20
  has_matching_runbook: true
  fragile_service: null
---

checkout-api: elevated latency or errors tracing to one specific upstream call. Onset was within the last monitoring window -- investigate before it breaches SLO further.
