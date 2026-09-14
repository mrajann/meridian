---
doc_id: postmortem-inventory-service-oversell
doc_type: postmortem
title: 'Postmortem: inventory-service oversell during flash sale'
services:
- inventory-service
metadata:
  root_cause_service: inventory-service
  root_cause_category: race_condition
  affected_services:
  - cart-service
  fragile_service: null
---

Summary: a limited-stock item was oversold by 40 units during a flash sale due to a race condition in stock reservation.

Root cause: two concurrent reservation requests for the same SKU both read the pre-decrement stock count before either write committed, allowing both to reserve the last unit.

Action items: move stock reservation to a single atomic decrement query instead of read-then-write.
