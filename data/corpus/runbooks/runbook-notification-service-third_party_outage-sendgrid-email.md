---
doc_id: runbook-notification-service-third_party_outage-sendgrid-email
doc_type: runbook
title: 'notification-service: third party outage (sendgrid-email root cause)'
services:
- notification-service
metadata:
  root_cause_category: third_party_outage__sendgrid-email
---

notification-service is showing requests to an external provider failing or timing out. Check the notification-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: sendgrid-email is degraded, so email notifications are failing to send.

Fix: check SendGrid's status page; there is no internal fix while the provider is degraded.
