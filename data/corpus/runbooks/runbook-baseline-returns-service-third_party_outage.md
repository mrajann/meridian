---
doc_id: runbook-baseline-returns-service-third_party_outage
doc_type: runbook
title: 'returns-service: third party outage'
services:
- returns-service
metadata:
  root_cause_category: third_party_outage
---

returns-service is showing requests to an external provider failing or timing out. Check orders-service first -- returns-service depends on it directly. Check the returns-service dashboard and recent deploys via ci-pipeline before assuming the fault is in returns-service itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting returns-service -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: Customers cannot initiate returns. No impact to ordering or shipping.
