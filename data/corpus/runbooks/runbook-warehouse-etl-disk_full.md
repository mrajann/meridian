---
doc_id: runbook-warehouse-etl-disk_full
doc_type: runbook
title: 'warehouse-etl: disk full'
services:
- warehouse-etl
metadata:
  root_cause_category: disk_full
---

warehouse-etl is showing writes being refused or new work no longer being accepted. Check postgres-replica first -- warehouse-etl depends on it directly. Check the warehouse-etl dashboard and recent deploys via ci-pipeline before assuming the fault is in warehouse-etl itself.

Likely cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting warehouse-etl -- a restart will not fix disk full if the underlying condition is still present.

Blast radius: Analytics and reporting data goes stale. No customer-facing impact.
