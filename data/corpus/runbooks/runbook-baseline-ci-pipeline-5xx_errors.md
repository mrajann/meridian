---
doc_id: runbook-baseline-ci-pipeline-5xx_errors
doc_type: runbook
title: 'ci-pipeline: 5xx errors'
services:
- ci-pipeline
metadata:
  root_cause_category: 5xx_errors
---

ci-pipeline is showing an elevated 5xx error rate. Check secrets-manager first -- ci-pipeline depends on it directly. Check the ci-pipeline dashboard and recent deploys via ci-pipeline before assuming the fault is in ci-pipeline itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting ci-pipeline -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Deploys are blocked. No impact to already-running services.
