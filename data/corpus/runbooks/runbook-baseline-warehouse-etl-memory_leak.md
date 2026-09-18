---
doc_id: runbook-baseline-warehouse-etl-memory_leak
doc_type: runbook
title: 'warehouse-etl: memory leak'
services:
- warehouse-etl
metadata:
  root_cause_category: memory_leak
---

warehouse-etl is showing gradually increasing memory usage and periodic restarts. Check postgres-replica first -- warehouse-etl depends on it directly. Check the warehouse-etl dashboard and recent deploys via ci-pipeline before assuming the fault is in warehouse-etl itself.

Likely cause: a memory leak accumulates until the process is killed for excess memory use and restarts.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting warehouse-etl -- a restart will not fix memory leak if the underlying condition is still present.

Blast radius: Analytics and reporting data goes stale. No customer-facing impact.
