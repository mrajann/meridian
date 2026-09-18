---
doc_id: runbook-baseline-redis-cache-job_failure
doc_type: runbook
title: 'redis-cache: job failure'
services:
- redis-cache
metadata:
  root_cause_category: job_failure
---

redis-cache is showing a batch or background job no longer producing fresh output. Check the redis-cache dashboard and recent deploys via ci-pipeline before assuming the fault is in redis-cache itself.

Likely cause: the job has been failing without alerting directly on job failure.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting redis-cache -- a restart will not fix job failure if the underlying condition is still present.

Blast radius: Elevated latency and error rates across most core-business services.
