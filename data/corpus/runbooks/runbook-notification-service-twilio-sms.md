---
doc_id: runbook-notification-service-twilio-sms
doc_type: runbook
title: 'notification-service: requests to an external provider failing or timing out
  (twilio-sms root cause)'
services:
- notification-service
metadata:
  root_cause_category: third_party_outage__twilio-sms
---

notification-service is showing requests to an external provider failing or timing out. Check the notification-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: twilio-sms is degraded or unavailable, so notification-service's calls to it are failing or timing out.

Fix: check twilio-sms health directly before touching notification-service itself.
