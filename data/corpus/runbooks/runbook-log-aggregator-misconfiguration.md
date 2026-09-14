---
doc_id: runbook-log-aggregator-misconfiguration
doc_type: runbook
title: 'log-aggregator: misconfiguration'
services:
- log-aggregator
metadata:
  root_cause_category: misconfiguration
---

log-aggregator is showing unexpected behavior with no code change involved. Check kafka-broker first -- log-aggregator depends on it directly. Check the log-aggregator dashboard and recent deploys via ci-pipeline before assuming the fault is in log-aggregator itself.

Likely cause: a configuration change had a broader blast radius than intended.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting log-aggregator -- a restart will not fix misconfiguration if the underlying condition is still present.

Blast radius: Logs delayed or missing. No impact to serving traffic; hurts debugging.
