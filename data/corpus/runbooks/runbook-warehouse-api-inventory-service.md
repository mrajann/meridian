---
doc_id: runbook-warehouse-api-inventory-service
doc_type: runbook
title: 'warehouse-api: an elevated 5xx error rate (inventory-service root cause)'
services:
- warehouse-api
metadata:
  root_cause_category: 5xx_errors__inventory-service
---

warehouse-api is showing an elevated 5xx error rate. Check the warehouse-api dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: inventory-service is degraded or unavailable, so warehouse-api's calls to it are failing or timing out.

Fix: check inventory-service health directly before touching warehouse-api itself.
