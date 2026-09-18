---
doc_id: runbook-baseline-metrics-collector-certificate_expiry
doc_type: runbook
title: 'metrics-collector: certificate expiry'
services:
- metrics-collector
metadata:
  root_cause_category: certificate_expiry
---

metrics-collector is showing auth or TLS failures with no code change involved. Check kafka-broker first -- metrics-collector depends on it directly. Check the metrics-collector dashboard and recent deploys via ci-pipeline before assuming the fault is in metrics-collector itself.

Likely cause: a certificate expired without being auto-rotated in time.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting metrics-collector -- a restart will not fix certificate expiry if the underlying condition is still present.

Blast radius: Metrics and alerting degrade; services keep serving traffic normally.
