---
doc_id: runbook-cascade-root-cause-postgres-primary-replication_lag
doc_type: runbook
title: 'postgres-primary: reads returning stale or out-of-date data (cascading)'
services:
- postgres-primary
metadata:
  root_cause_category: replication_lag
---

postgres-primary is showing reads returning stale or out-of-date data. Because so many services depend on postgres-primary directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single postgres-primary alert -- treat a burst of simultaneous cross-service errors as one postgres-primary incident, not several.

Root cause: the replica has fallen behind the primary, usually from a long-running query blocking replay.

Fix: resolve the condition on postgres-primary directly; the downstream services will recover on their own once it does.
