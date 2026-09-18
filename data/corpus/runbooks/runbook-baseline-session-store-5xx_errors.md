---
doc_id: runbook-baseline-session-store-5xx_errors
doc_type: runbook
title: 'session-store: 5xx errors'
services:
- session-store
metadata:
  root_cause_category: 5xx_errors
---

session-store is showing an elevated 5xx error rate. Check redis-cache first -- session-store depends on it directly. Check the session-store dashboard and recent deploys via ci-pipeline before assuming the fault is in session-store itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting session-store -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Users get logged out unexpectedly; new logins may fail.
