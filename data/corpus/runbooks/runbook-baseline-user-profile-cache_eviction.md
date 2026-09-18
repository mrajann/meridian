---
doc_id: runbook-baseline-user-profile-cache_eviction
doc_type: runbook
title: 'user-profile: cache eviction'
services:
- user-profile
metadata:
  root_cause_category: cache_eviction
---

user-profile is showing elevated latency and a rise in cold-cache misses. Check postgres-primary first -- user-profile depends on it directly. Check the user-profile dashboard and recent deploys via ci-pipeline before assuming the fault is in user-profile itself.

Likely cause: an eviction policy or memory limit change is evicting entries faster than expected.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting user-profile -- a restart will not fix cache eviction if the underlying condition is still present.

Blast radius: Customers cannot view or edit profile/address data.
