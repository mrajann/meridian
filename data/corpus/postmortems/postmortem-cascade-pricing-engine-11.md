---
doc_id: postmortem-cascade-pricing-engine-11
doc_type: postmortem
title: 'Postmortem: pricing-engine cascade (inconsistent or duplicated state under
  concurrent load)'
services:
- pricing-engine
- cart-service
- checkout-api
- mobile-api
- orders-service
- returns-service
- shipping-service
metadata:
  root_cause_service: pricing-engine
  root_cause_category: race_condition
  affected_services:
  - cart-service
  - checkout-api
  - mobile-api
  - orders-service
  - returns-service
  - shipping-service
  fragile_service: null
  adversarial_case: cascading_failure
---

Summary: pricing-engine experienced inconsistent or duplicated state under concurrent load. This produced symptoms in 6 dependent services at once: cart-service, checkout-api, mobile-api, orders-service, returns-service, shipping-service.

Root cause: two concurrent operations both read stale state before either write committed.

On-call for several of the affected services were paged independently before the shared root cause on pricing-engine was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on pricing-engine rather than relying on downstream symptoms to surface a shared root cause.
