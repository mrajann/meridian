---
doc_id: runbook-notification-service-delivery-failure
doc_type: runbook
title: 'notification-service: delivery failures'
services:
- notification-service
- twilio-sms
- sendgrid-email
metadata:
  root_cause_category: third_party_outage
---

Customers are not receiving order or shipping notifications. notification-service itself is almost never the root cause -- it depends on exactly two third parties, twilio-sms and sendgrid-email, and a failure in either one presents identically from notification-service's own metrics (queue backlog growing, delivery confirmations not coming back).

Fix: check twilio-sms's and sendgrid-email's public status pages first. If one is degraded, there is no internal fix -- confirm notification-service is retrying with backoff rather than dropping messages, and communicate the expected delay. Do not page data-platform or restart notification-service itself unless both providers report healthy.
