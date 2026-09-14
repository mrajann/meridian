---
doc_id: runbook-cdn-config-latency_spike
doc_type: runbook
title: 'cdn-config: latency spike'
services:
- cdn-config
metadata:
  root_cause_category: latency_spike
---

cdn-config is showing p99 latency above its SLO target. Check cloudflare-cdn first -- cdn-config depends on it directly. Check the cdn-config dashboard and recent deploys via ci-pipeline before assuming the fault is in cdn-config itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting cdn-config -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Stale or broken content served at the edge; asset load failures.
