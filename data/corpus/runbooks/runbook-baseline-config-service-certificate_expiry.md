---
doc_id: runbook-baseline-config-service-certificate_expiry
doc_type: runbook
title: 'config-service: certificate expiry'
services:
- config-service
metadata:
  root_cause_category: certificate_expiry
---

config-service is showing auth or TLS failures with no code change involved. Check postgres-primary first -- config-service depends on it directly. Check the config-service dashboard and recent deploys via ci-pipeline before assuming the fault is in config-service itself.

Likely cause: a certificate expired without being auto-rotated in time.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting config-service -- a restart will not fix certificate expiry if the underlying condition is still present.

Blast radius: Services fall back to cached/default config; new config changes don't apply.
