---
doc_id: runbook-baseline-postgres-replica-memory_leak
doc_type: runbook
title: 'postgres-replica: memory leak'
services:
- postgres-replica
metadata:
  root_cause_category: memory_leak
---

postgres-replica is showing gradually increasing memory usage and periodic restarts. Check postgres-primary first -- postgres-replica depends on it directly. Check the postgres-replica dashboard and recent deploys via ci-pipeline before assuming the fault is in postgres-replica itself.

Likely cause: a memory leak accumulates until the process is killed for excess memory use and restarts.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting postgres-replica -- a restart will not fix memory leak if the underlying condition is still present.

Blast radius: Search, analytics, and RAG retrieval see stale or slow reads.
