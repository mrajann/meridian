---
doc_id: runbook-feature-flags-misconfiguration
doc_type: runbook
title: 'feature-flags: misconfiguration'
services:
- feature-flags
metadata:
  root_cause_category: misconfiguration
---

feature-flags is showing unexpected behavior with no code change involved. Check redis-cache first -- feature-flags depends on it directly. Check the feature-flags dashboard and recent deploys via ci-pipeline before assuming the fault is in feature-flags itself.

Likely cause: a configuration change had a broader blast radius than intended.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting feature-flags -- a restart will not fix misconfiguration if the underlying condition is still present.

Blast radius: Flag evaluations fall back to defaults; rollouts and kill switches stop working.
