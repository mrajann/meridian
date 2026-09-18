---
doc_id: runbook-baseline-feature-flags-certificate_expiry
doc_type: runbook
title: 'feature-flags: certificate expiry'
services:
- feature-flags
metadata:
  root_cause_category: certificate_expiry
---

feature-flags is showing auth or TLS failures with no code change involved. Check redis-cache first -- feature-flags depends on it directly. Check the feature-flags dashboard and recent deploys via ci-pipeline before assuming the fault is in feature-flags itself.

Likely cause: a certificate expired without being auto-rotated in time.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting feature-flags -- a restart will not fix certificate expiry if the underlying condition is still present.

Blast radius: Flag evaluations fall back to defaults; rollouts and kill switches stop working.
