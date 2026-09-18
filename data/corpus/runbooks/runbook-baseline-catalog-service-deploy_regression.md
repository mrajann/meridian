---
doc_id: runbook-baseline-catalog-service-deploy_regression
doc_type: runbook
title: 'catalog-service: deploy regression'
services:
- catalog-service
metadata:
  root_cause_category: deploy_regression
---

catalog-service is showing a symptom that started immediately after a deploy. Check postgres-primary first -- catalog-service depends on it directly. Check the catalog-service dashboard and recent deploys via ci-pipeline before assuming the fault is in catalog-service itself.

Likely cause: the most recent deploy introduced a regression.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting catalog-service -- a restart will not fix deploy regression if the underlying condition is still present.

Blast radius: Product pages fail to load or show missing/stale data.
