---
doc_id: postmortem-cascade-inventory-service-10
doc_type: postmortem
title: 'Postmortem: inventory-service cascade (an elevated 5xx error rate)'
services:
- inventory-service
- cart-service
- checkout-api
- mobile-api
- orders-service
- returns-service
- shipping-service
metadata:
  root_cause_service: inventory-service
  root_cause_category: 5xx_errors
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

Summary: inventory-service experienced an elevated 5xx error rate. This produced symptoms in 6 dependent services at once: cart-service, checkout-api, mobile-api, orders-service, returns-service, shipping-service.

Root cause: an unhandled exception path was hit under production load that testing never exercised.

On-call for several of the affected services were paged independently before the shared root cause on inventory-service was identified -- this is one incident, not 6 separate ones.

Action items: alert directly on inventory-service rather than relying on downstream symptoms to surface a shared root cause.
