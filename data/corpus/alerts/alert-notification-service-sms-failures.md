---
doc_id: alert-notification-service-sms-failures
doc_type: alert
title: 'notification-service: SMS delivery confirmation rate below 50%'
services:
- notification-service
metadata:
  root_cause_service: twilio-sms
  root_cause_category: third_party_outage
  correct_runbook: runbook-notification-service-delivery-failure
  has_matching_runbook: true
  fragile_service: notification-service
---

notification-service SMS delivery confirmation rate dropped to 12% over the last 30 minutes, threshold 50%. Email delivery confirmation rate is unaffected at 98%. Queue depth for the SMS channel is climbing.
