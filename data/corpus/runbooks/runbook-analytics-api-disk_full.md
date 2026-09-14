---
doc_id: runbook-analytics-api-disk_full
doc_type: runbook
title: 'analytics-api: disk full'
services:
- analytics-api
metadata:
  root_cause_category: disk_full
---

analytics-api is showing writes being refused or new work no longer being accepted. Check warehouse-etl first -- analytics-api depends on it directly. Check the analytics-api dashboard and recent deploys via ci-pipeline before assuming the fault is in analytics-api itself.

Likely cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting analytics-api -- a restart will not fix disk full if the underlying condition is still present.

Blast radius: Internal dashboards unavailable or stale. No customer-facing impact.
