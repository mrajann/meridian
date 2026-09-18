---
doc_id: runbook-cascade-root-cause-inventory-service-5xx_errors
doc_type: runbook
title: 'inventory-service: an elevated 5xx error rate (cascading)'
services:
- inventory-service
metadata:
  root_cause_category: 5xx_errors
---

inventory-service is showing an elevated 5xx error rate. Because so many services depend on inventory-service directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single inventory-service alert -- treat a burst of simultaneous cross-service errors as one inventory-service incident, not several.

Root cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: resolve the condition on inventory-service directly; the downstream services will recover on their own once it does.
