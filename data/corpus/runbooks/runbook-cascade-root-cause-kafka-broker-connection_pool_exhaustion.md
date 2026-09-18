---
doc_id: runbook-cascade-root-cause-kafka-broker-connection_pool_exhaustion
doc_type: runbook
title: 'kafka-broker: requests stalling while waiting on a database connection (cascading)'
services:
- kafka-broker
metadata:
  root_cause_category: connection_pool_exhaustion
---

kafka-broker is showing requests stalling while waiting on a database connection. Because so many services depend on kafka-broker directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single kafka-broker alert -- treat a burst of simultaneous cross-service errors as one kafka-broker incident, not several.

Root cause: the connection pool is undersized for current traffic and connections are maxed out.

Fix: resolve the condition on kafka-broker directly; the downstream services will recover on their own once it does.
