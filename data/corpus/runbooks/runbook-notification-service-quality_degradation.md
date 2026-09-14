---
doc_id: runbook-notification-service-quality_degradation
doc_type: runbook
title: 'notification-service: quality degradation'
services:
- notification-service
metadata:
  root_cause_category: quality_degradation
---

notification-service is showing output quality dropping with no traditional error signal. Check twilio-sms first -- notification-service depends on it directly. Check the notification-service dashboard and recent deploys via ci-pipeline before assuming the fault is in notification-service itself.

Likely cause: a routing or model-version change degraded output quality without tripping a health check.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting notification-service -- a restart will not fix quality degradation if the underlying condition is still present.

Blast radius: Customers stop receiving order/shipping updates. Orders still process normally.
