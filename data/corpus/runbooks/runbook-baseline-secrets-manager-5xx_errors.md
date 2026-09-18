---
doc_id: runbook-baseline-secrets-manager-5xx_errors
doc_type: runbook
title: 'secrets-manager: 5xx errors'
services:
- secrets-manager
metadata:
  root_cause_category: 5xx_errors
---

secrets-manager is showing an elevated 5xx error rate. Check the secrets-manager dashboard and recent deploys via ci-pipeline before assuming the fault is in secrets-manager itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting secrets-manager -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Services with expiring credentials begin failing auth to their dependencies.
