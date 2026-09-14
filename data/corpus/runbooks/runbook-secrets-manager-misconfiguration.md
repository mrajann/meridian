---
doc_id: runbook-secrets-manager-misconfiguration
doc_type: runbook
title: 'secrets-manager: misconfiguration'
services:
- secrets-manager
metadata:
  root_cause_category: misconfiguration
---

secrets-manager is showing unexpected behavior with no code change involved. Check the secrets-manager dashboard and recent deploys via ci-pipeline before assuming the fault is in secrets-manager itself.

Likely cause: a configuration change had a broader blast radius than intended.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting secrets-manager -- a restart will not fix misconfiguration if the underlying condition is still present.

Blast radius: Services with expiring credentials begin failing auth to their dependencies.
