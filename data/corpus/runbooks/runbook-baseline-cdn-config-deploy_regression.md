---
doc_id: runbook-baseline-cdn-config-deploy_regression
doc_type: runbook
title: 'cdn-config: deploy regression'
services:
- cdn-config
metadata:
  root_cause_category: deploy_regression
---

cdn-config is showing a symptom that started immediately after a deploy. Check cloudflare-cdn first -- cdn-config depends on it directly. Check the cdn-config dashboard and recent deploys via ci-pipeline before assuming the fault is in cdn-config itself.

Likely cause: the most recent deploy introduced a regression.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting cdn-config -- a restart will not fix deploy regression if the underlying condition is still present.

Blast radius: Stale or broken content served at the edge; asset load failures.
