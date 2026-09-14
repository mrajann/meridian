---
doc_id: runbook-metrics-collector-misconfiguration
doc_type: runbook
title: 'metrics-collector: misconfiguration'
services:
- metrics-collector
metadata:
  root_cause_category: misconfiguration
---

metrics-collector is showing unexpected behavior with no code change involved. Check kafka-broker first -- metrics-collector depends on it directly. Check the metrics-collector dashboard and recent deploys via ci-pipeline before assuming the fault is in metrics-collector itself.

Likely cause: a configuration change had a broader blast radius than intended.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting metrics-collector -- a restart will not fix misconfiguration if the underlying condition is still present.

Blast radius: Metrics and alerting degrade; services keep serving traffic normally.
