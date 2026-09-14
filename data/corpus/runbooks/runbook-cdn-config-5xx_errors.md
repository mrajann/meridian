---
doc_id: runbook-cdn-config-5xx_errors
doc_type: runbook
title: 'cdn-config: 5xx errors'
services:
- cdn-config
metadata:
  root_cause_category: 5xx_errors
---

cdn-config is showing an elevated 5xx error rate. Check cloudflare-cdn first -- cdn-config depends on it directly. Check the cdn-config dashboard and recent deploys via ci-pipeline before assuming the fault is in cdn-config itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting cdn-config -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Stale or broken content served at the edge; asset load failures.
