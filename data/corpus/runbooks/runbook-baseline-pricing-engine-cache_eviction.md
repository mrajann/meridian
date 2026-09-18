---
doc_id: runbook-baseline-pricing-engine-cache_eviction
doc_type: runbook
title: 'pricing-engine: cache eviction'
services:
- pricing-engine
metadata:
  root_cause_category: cache_eviction
---

pricing-engine is showing elevated latency and a rise in cold-cache misses. Check postgres-primary first -- pricing-engine depends on it directly. Check the pricing-engine dashboard and recent deploys via ci-pipeline before assuming the fault is in pricing-engine itself.

Likely cause: an eviction policy or memory limit change is evicting entries faster than expected.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting pricing-engine -- a restart will not fix cache eviction if the underlying condition is still present.

Blast radius: Checkout may show incorrect prices or fail to price the cart.
