---
doc_id: alert-cascade-kafka-broker-12
doc_type: alert
title: 5xx spike across 6 services simultaneously
services:
- log-aggregator
- metrics-collector
- notification-service
- orders-service
- returns-service
- shipping-service
metadata:
  root_cause_service: kafka-broker
  root_cause_category: connection_pool_exhaustion
  correct_runbook: runbook-cascade-root-cause-kafka-broker-connection_pool_exhaustion
  has_matching_runbook: true
  affected_services:
  - log-aggregator
  - metrics-collector
  - notification-service
  - orders-service
  - returns-service
  - shipping-service
  fragile_service: null
  adversarial_case: cascading_failure
---

Simultaneous error-rate increase across log-aggregator, metrics-collector, notification-service, orders-service, returns-service, shipping-service, all starting within the same 60-second window. All depend on kafka-broker, directly or transitively.
