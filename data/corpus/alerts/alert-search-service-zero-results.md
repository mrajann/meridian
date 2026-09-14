---
doc_id: alert-search-service-zero-results
doc_type: alert
title: 'search-service: zero-result rate above 15% for a subset of queries'
services:
- search-service
metadata:
  root_cause_service: search-service
  root_cause_category: stale_index
  correct_runbook: null
  has_matching_runbook: false
  fragile_service: null
---

search-service is returning zero results for roughly 18% of queries containing recently-added product terms, while overall error rate and latency are both normal. Affects search only -- browsing by category still returns correct results.
