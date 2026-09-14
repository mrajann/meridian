---
doc_id: runbook-notification-service-third_party_outage-twilio-sms
doc_type: runbook
title: 'notification-service: third party outage (twilio-sms root cause)'
services:
- notification-service
metadata:
  root_cause_category: third_party_outage__twilio-sms
---

notification-service is showing requests to an external provider failing or timing out. Check the notification-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: twilio-sms is degraded, so SMS notifications are failing to send.

Fix: check status.twilio.com; there is no internal fix while the provider is degraded.
