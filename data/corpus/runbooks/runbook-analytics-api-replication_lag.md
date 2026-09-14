---
doc_id: runbook-analytics-api-replication_lag
doc_type: runbook
title: 'analytics-api: replication lag'
services:
- analytics-api
metadata:
  root_cause_category: replication_lag
---

analytics-api is showing reads returning stale or out-of-date data. Check warehouse-etl first -- analytics-api depends on it directly. Check the analytics-api dashboard and recent deploys via ci-pipeline before assuming the fault is in analytics-api itself.

Likely cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting analytics-api -- a restart will not fix replication lag if the underlying condition is still present.

Blast radius: Internal dashboards unavailable or stale. No customer-facing impact.
