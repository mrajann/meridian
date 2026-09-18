---
doc_id: runbook-baseline-config-service-5xx_errors
doc_type: runbook
title: 'config-service: 5xx errors'
services:
- config-service
metadata:
  root_cause_category: 5xx_errors
---

config-service is showing an elevated 5xx error rate. Check postgres-primary first -- config-service depends on it directly. Check the config-service dashboard and recent deploys via ci-pipeline before assuming the fault is in config-service itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting config-service -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Services fall back to cached/default config; new config changes don't apply.
