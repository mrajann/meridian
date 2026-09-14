---
doc_id: runbook-notification-service-stale_data
doc_type: runbook
title: 'notification-service: stale data'
services:
- notification-service
metadata:
  root_cause_category: stale_data
---

notification-service is showing results or dashboards reflecting outdated state with no errors thrown. Check twilio-sms first -- notification-service depends on it directly. Check the notification-service dashboard and recent deploys via ci-pipeline before assuming the fault is in notification-service itself.

Likely cause: a background refresh or index job has been failing silently.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting notification-service -- a restart will not fix stale data if the underlying condition is still present.

Blast radius: Customers stop receiving order/shipping updates. Orders still process normally.
