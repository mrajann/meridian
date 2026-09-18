---
doc_id: runbook-pricing-engine-redis-cache
doc_type: runbook
title: 'pricing-engine: an elevated 5xx error rate (redis-cache root cause)'
services:
- pricing-engine
metadata:
  root_cause_category: 5xx_errors__redis-cache
---

pricing-engine is showing an elevated 5xx error rate. Check the pricing-engine dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: redis-cache is degraded or unavailable, so pricing-engine's calls to it are failing or timing out.

Fix: check redis-cache health directly before touching pricing-engine itself.
