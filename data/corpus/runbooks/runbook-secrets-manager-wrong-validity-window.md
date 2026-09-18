---
doc_id: runbook-secrets-manager-wrong-validity-window
doc_type: runbook
title: 'secrets-manager: auth or TLS failures with no code change involved (wrong-validity-window
  root cause)'
services:
- secrets-manager
metadata:
  root_cause_category: certificate_expiry__wrong-validity-window
---

secrets-manager is showing auth or TLS failures with no code change involved. Check the secrets-manager dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: the certificate was issued with a shorter validity window than the rotation schedule assumed.

Fix: issue a new certificate and correct the rotation schedule to match the actual validity window.
