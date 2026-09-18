---
doc_id: runbook-baseline-log-aggregator-certificate_expiry
doc_type: runbook
title: 'log-aggregator: certificate expiry'
services:
- log-aggregator
metadata:
  root_cause_category: certificate_expiry
---

log-aggregator is showing auth or TLS failures with no code change involved. Check kafka-broker first -- log-aggregator depends on it directly. Check the log-aggregator dashboard and recent deploys via ci-pipeline before assuming the fault is in log-aggregator itself.

Likely cause: a certificate expired without being auto-rotated in time.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting log-aggregator -- a restart will not fix certificate expiry if the underlying condition is still present.

Blast radius: Logs delayed or missing. No impact to serving traffic; hurts debugging.
