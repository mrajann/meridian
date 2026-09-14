---
doc_id: alert-notification-service-latency_spike
doc_type: alert
title: 'notification-service: p99 latency above its SLO target'
services:
- notification-service
metadata:
  root_cause_service: notification-service
  root_cause_category: latency_spike
  correct_runbook: runbook-notification-service-latency_spike
  has_matching_runbook: true
  fragile_service: notification-service
---

notification-service: p99 latency above its SLO target. Onset was within the last monitoring window -- investigate before it breaches SLO further.
