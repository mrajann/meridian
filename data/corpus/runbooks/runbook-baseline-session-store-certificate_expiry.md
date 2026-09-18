---
doc_id: runbook-baseline-session-store-certificate_expiry
doc_type: runbook
title: 'session-store: certificate expiry'
services:
- session-store
metadata:
  root_cause_category: certificate_expiry
---

session-store is showing auth or TLS failures with no code change involved. Check redis-cache first -- session-store depends on it directly. Check the session-store dashboard and recent deploys via ci-pipeline before assuming the fault is in session-store itself.

Likely cause: a certificate expired without being auto-rotated in time.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting session-store -- a restart will not fix certificate expiry if the underlying condition is still present.

Blast radius: Users get logged out unexpectedly; new logins may fail.
