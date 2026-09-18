---
doc_id: postmortem-baseline-postgres-primary-memory_leak-3
doc_type: postmortem
title: 'Postmortem: postgres-primary memory leak (incident #3)'
services:
- postgres-primary
metadata:
  root_cause_service: postgres-primary
  root_cause_category: memory_leak
  affected_services: []
  fragile_service: postgres-primary
---

Summary: postgres-primary experienced gradually increasing memory usage and periodic restarts. This is recorded incident #3 of this type for postgres-primary.

Root cause: a memory leak accumulates until the process is killed for excess memory use and restarts.

Action items: add direct alerting on this failure mode for postgres-primary rather than relying on downstream symptoms to surface it.
