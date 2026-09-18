---
doc_id: runbook-secrets-manager-rotation-failure
doc_type: runbook
title: 'secrets-manager: auth or TLS failures with no code change involved (rotation-failure
  root cause)'
services:
- secrets-manager
metadata:
  root_cause_category: certificate_expiry__rotation-failure
---

secrets-manager is showing auth or TLS failures with no code change involved. Check the secrets-manager dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: the automated rotation job silently failed and the old certificate expired before anyone noticed.

Fix: issue a new certificate manually and fix the rotation job's alerting so this fails loudly next time.
