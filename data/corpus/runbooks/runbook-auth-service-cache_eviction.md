---
doc_id: runbook-auth-service-cache_eviction
doc_type: runbook
title: 'auth-service: cache eviction'
services:
- auth-service
metadata:
  root_cause_category: cache_eviction
---

auth-service is showing elevated latency and a rise in cold-cache misses. Check postgres-primary first -- auth-service depends on it directly. Check the auth-service dashboard and recent deploys via ci-pipeline before assuming the fault is in auth-service itself.

Likely cause: an eviction policy or memory limit change is evicting entries faster than expected.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting auth-service -- a restart will not fix cache eviction if the underlying condition is still present.

Blast radius: No one can log in. Cascades to every service behind api-gateway.
