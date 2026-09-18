---
doc_id: runbook-baseline-notification-service-latency_spike
doc_type: runbook
title: 'notification-service: latency spike'
services:
- notification-service
metadata:
  root_cause_category: latency_spike
---

notification-service is showing p99 latency above its SLO target. Check twilio-sms first -- notification-service depends on it directly. Check the notification-service dashboard and recent deploys via ci-pipeline before assuming the fault is in notification-service itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting notification-service -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Customers stop receiving order/shipping updates. Orders still process normally.
