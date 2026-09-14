---
doc_id: runbook-cloudflare-cdn-third_party_outage
doc_type: runbook
title: 'cloudflare-cdn: third party outage'
services:
- cloudflare-cdn
metadata:
  root_cause_category: third_party_outage
---

cloudflare-cdn is showing requests to an external provider failing or timing out. Check the cloudflare-cdn dashboard and recent deploys via ci-pipeline before assuming the fault is in cloudflare-cdn itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting cloudflare-cdn -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: Degraded or unreachable storefront for customers behind affected PoPs.
