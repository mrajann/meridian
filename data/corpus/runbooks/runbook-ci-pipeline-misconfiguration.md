---
doc_id: runbook-ci-pipeline-misconfiguration
doc_type: runbook
title: 'ci-pipeline: misconfiguration'
services:
- ci-pipeline
metadata:
  root_cause_category: misconfiguration
---

ci-pipeline is showing unexpected behavior with no code change involved. Check secrets-manager first -- ci-pipeline depends on it directly. Check the ci-pipeline dashboard and recent deploys via ci-pipeline before assuming the fault is in ci-pipeline itself.

Likely cause: a configuration change had a broader blast radius than intended.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting ci-pipeline -- a restart will not fix misconfiguration if the underlying condition is still present.

Blast radius: Deploys are blocked. No impact to already-running services.
