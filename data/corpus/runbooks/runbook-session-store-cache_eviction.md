---
doc_id: runbook-session-store-cache_eviction
doc_type: runbook
title: 'session-store: cache eviction'
services:
- session-store
metadata:
  root_cause_category: cache_eviction
---

session-store is showing elevated latency and a rise in cold-cache misses. Check redis-cache first -- session-store depends on it directly. Check the session-store dashboard and recent deploys via ci-pipeline before assuming the fault is in session-store itself.

Likely cause: an eviction policy or memory limit change is evicting entries faster than expected.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting session-store -- a restart will not fix cache eviction if the underlying condition is still present.

Blast radius: Users get logged out unexpectedly; new logins may fail.
