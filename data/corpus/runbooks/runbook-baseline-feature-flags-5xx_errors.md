---
doc_id: runbook-baseline-feature-flags-5xx_errors
doc_type: runbook
title: 'feature-flags: 5xx errors'
services:
- feature-flags
metadata:
  root_cause_category: 5xx_errors
---

feature-flags is showing an elevated 5xx error rate. Check redis-cache first -- feature-flags depends on it directly. Check the feature-flags dashboard and recent deploys via ci-pipeline before assuming the fault is in feature-flags itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting feature-flags -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Flag evaluations fall back to defaults; rollouts and kill switches stop working.
