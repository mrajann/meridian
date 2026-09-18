---
doc_id: runbook-tracking-service-postgres-replica
doc_type: runbook
title: 'tracking-service: an elevated 5xx error rate (postgres-replica root cause)'
services:
- tracking-service
metadata:
  root_cause_category: 5xx_errors__postgres-replica
---

tracking-service is showing an elevated 5xx error rate. Check the tracking-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-replica is degraded or unavailable, so tracking-service's calls to it are failing or timing out.

Fix: check postgres-replica health directly before touching tracking-service itself.
