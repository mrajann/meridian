---
doc_id: alert-near-dup-notification-service
doc_type: alert
title: 'notification-service: requests to an external provider failing or timing out'
services:
- notification-service
metadata:
  root_cause_service: notification-service
  root_cause_category: third_party_outage__twilio-sms
  correct_runbook: runbook-notification-service-twilio-sms
  has_matching_runbook: true
  fragile_service: notification-service
  adversarial_case: near_duplicate_pair
---

notification-service: requests to an external provider failing or timing out. Onset within the last monitoring window.
