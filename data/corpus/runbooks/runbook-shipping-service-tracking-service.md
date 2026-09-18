---
doc_id: runbook-shipping-service-tracking-service
doc_type: runbook
title: 'shipping-service: an elevated 5xx error rate (tracking-service root cause)'
services:
- shipping-service
metadata:
  root_cause_category: 5xx_errors__tracking-service
---

shipping-service is showing an elevated 5xx error rate. Check the shipping-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: tracking-service is degraded or unavailable, so shipping-service's calls to it are failing or timing out.

Fix: check tracking-service health directly before touching shipping-service itself.
