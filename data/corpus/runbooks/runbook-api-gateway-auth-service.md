---
doc_id: runbook-api-gateway-auth-service
doc_type: runbook
title: 'api-gateway: an elevated 5xx error rate (auth-service root cause)'
services:
- api-gateway
metadata:
  root_cause_category: 5xx_errors__auth-service
---

api-gateway is showing an elevated 5xx error rate. Check the api-gateway dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: auth-service is degraded or unavailable, so api-gateway's calls to it are failing or timing out.

Fix: check auth-service health directly before touching api-gateway itself.
