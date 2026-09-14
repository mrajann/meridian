---
doc_id: runbook-search-service-5xx
doc_type: runbook
title: 'search-service: elevated 5xx rate'
services:
- search-service
metadata:
  root_cause_category: 5xx_errors
---

search-service is returning 5xx responses to a meaningful fraction of queries. Check postgres-replica and redis-cache health first, since search-service depends on both. If neither shows errors, check search-service's own logs for unhandled exceptions in query parsing.

Fix: restart the affected search-service pods if the error is isolated to a subset of instances; if postgres-replica or redis-cache is unhealthy, resolve that first -- search-service will recover on its own once its dependencies do.
