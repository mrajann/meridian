---
doc_id: runbook-baseline-stripe-gateway-third_party_outage
doc_type: runbook
title: 'stripe-gateway: third party outage'
services:
- stripe-gateway
metadata:
  root_cause_category: third_party_outage
---

stripe-gateway is showing requests to an external provider failing or timing out. Check the stripe-gateway dashboard and recent deploys via ci-pipeline before assuming the fault is in stripe-gateway itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting stripe-gateway -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: No payments can be captured anywhere in the platform.
