---
doc_id: runbook-returns-service-schema_mismatch
doc_type: runbook
title: 'returns-service: schema mismatch'
services:
- returns-service
metadata:
  root_cause_category: schema_mismatch
---

returns-service is showing requests failing validation unexpectedly. Check orders-service first -- returns-service depends on it directly. Check the returns-service dashboard and recent deploys via ci-pipeline before assuming the fault is in returns-service itself.

Likely cause: a caller is still sending a previous version of the request schema.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting returns-service -- a restart will not fix schema mismatch if the underlying condition is still present.

Blast radius: Customers cannot initiate returns. No impact to ordering or shipping.
