---
doc_id: runbook-baseline-web-frontend-misconfiguration
doc_type: runbook
title: 'web-frontend: misconfiguration'
services:
- web-frontend
metadata:
  root_cause_category: misconfiguration
---

web-frontend is showing unexpected behavior with no code change involved. Check api-gateway first -- web-frontend depends on it directly. Check the web-frontend dashboard and recent deploys via ci-pipeline before assuming the fault is in web-frontend itself.

Likely cause: a configuration change had a broader blast radius than intended.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting web-frontend -- a restart will not fix misconfiguration if the underlying condition is still present.

Blast radius: Customers cannot browse or check out on the website. Mobile app unaffected.
