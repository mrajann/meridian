---
doc_id: runbook-cascade-root-cause-postgres-primary-disk_full
doc_type: runbook
title: 'postgres-primary: writes being refused or new work no longer being accepted
  (cascading)'
services:
- postgres-primary
metadata:
  root_cause_category: disk_full
---

postgres-primary is showing writes being refused or new work no longer being accepted. Because so many services depend on postgres-primary directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single postgres-primary alert -- treat a burst of simultaneous cross-service errors as one postgres-primary incident, not several.

Root cause: the data volume filled up, usually from unshipped WAL or an unvacuumed table.

Fix: resolve the condition on postgres-primary directly; the downstream services will recover on their own once it does.
