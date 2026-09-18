---
doc_id: runbook-api-gateway-feature-flags
doc_type: runbook
title: 'api-gateway: an elevated 5xx error rate (feature-flags root cause)'
services:
- api-gateway
metadata:
  root_cause_category: 5xx_errors__feature-flags
---

api-gateway is showing an elevated 5xx error rate. Check the api-gateway dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: feature-flags is degraded or unavailable, so api-gateway's calls to it are failing or timing out.

Fix: check feature-flags health directly before touching api-gateway itself.
