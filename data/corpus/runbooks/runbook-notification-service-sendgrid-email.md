---
doc_id: runbook-notification-service-sendgrid-email
doc_type: runbook
title: 'notification-service: requests to an external provider failing or timing out
  (sendgrid-email root cause)'
services:
- notification-service
metadata:
  root_cause_category: third_party_outage__sendgrid-email
---

notification-service is showing requests to an external provider failing or timing out. Check the notification-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: sendgrid-email is degraded or unavailable, so notification-service's calls to it are failing or timing out.

Fix: check sendgrid-email health directly before touching notification-service itself.
