---
doc_id: runbook-baseline-mobile-api-misconfiguration
doc_type: runbook
title: 'mobile-api: misconfiguration'
services:
- mobile-api
metadata:
  root_cause_category: misconfiguration
---

mobile-api is showing unexpected behavior with no code change involved. Check api-gateway first -- mobile-api depends on it directly. Check the mobile-api dashboard and recent deploys via ci-pipeline before assuming the fault is in mobile-api itself.

Likely cause: a configuration change had a broader blast radius than intended.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting mobile-api -- a restart will not fix misconfiguration if the underlying condition is still present.

Blast radius: Mobile app customers cannot browse or check out. Web storefront unaffected.
