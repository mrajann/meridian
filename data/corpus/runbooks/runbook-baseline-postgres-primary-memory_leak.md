---
doc_id: runbook-baseline-postgres-primary-memory_leak
doc_type: runbook
title: 'postgres-primary: memory leak'
services:
- postgres-primary
metadata:
  root_cause_category: memory_leak
---

postgres-primary is showing gradually increasing memory usage and periodic restarts. Check the postgres-primary dashboard and recent deploys via ci-pipeline before assuming the fault is in postgres-primary itself.

Likely cause: a memory leak accumulates until the process is killed for excess memory use and restarts.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting postgres-primary -- a restart will not fix memory leak if the underlying condition is still present.

Blast radius: All revenue. Nearly every core-business and platform service reads or writes here.
