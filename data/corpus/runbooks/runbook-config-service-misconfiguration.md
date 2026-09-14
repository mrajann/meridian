---
doc_id: runbook-config-service-misconfiguration
doc_type: runbook
title: 'config-service: misconfiguration'
services:
- config-service
metadata:
  root_cause_category: misconfiguration
---

config-service is showing unexpected behavior with no code change involved. Check postgres-primary first -- config-service depends on it directly. Check the config-service dashboard and recent deploys via ci-pipeline before assuming the fault is in config-service itself.

Likely cause: a configuration change had a broader blast radius than intended.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting config-service -- a restart will not fix misconfiguration if the underlying condition is still present.

Blast radius: Services fall back to cached/default config; new config changes don't apply.
