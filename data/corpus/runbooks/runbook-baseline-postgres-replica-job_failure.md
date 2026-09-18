---
doc_id: runbook-baseline-postgres-replica-job_failure
doc_type: runbook
title: 'postgres-replica: job failure'
services:
- postgres-replica
metadata:
  root_cause_category: job_failure
---

postgres-replica is showing a batch or background job no longer producing fresh output. Check postgres-primary first -- postgres-replica depends on it directly. Check the postgres-replica dashboard and recent deploys via ci-pipeline before assuming the fault is in postgres-replica itself.

Likely cause: the job has been failing without alerting directly on job failure.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting postgres-replica -- a restart will not fix job failure if the underlying condition is still present.

Blast radius: Search, analytics, and RAG retrieval see stale or slow reads.
