---
doc_id: postmortem-cascade-kafka-broker-12
doc_type: postmortem
title: 'Postmortem: kafka-broker cascade (requests stalling while waiting on a database
  connection)'
services:
- kafka-broker
- log-aggregator
- metrics-collector
- notification-service
- orders-service
- returns-service
- shipping-service
metadata:
  root_cause_service: kafka-broker
  root_cause_category: connection_pool_exhaustion
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

Summary: kafka-broker experienced requests stalling while waiting on a database connection. This produced symptoms in 6 dependent services at once: log-aggregator, metrics-collector, notification-service, orders-service, returns-service, shipping-service.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

On-call for several of the affected services were paged independently before the shared root cause on kafka-broker was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on kafka-broker rather than relying on downstream symptoms to surface a shared root cause.
