---
doc_id: catalog-entry-notification-service
doc_type: catalog_entry
title: 'Service catalog: notification-service'
services:
- notification-service
metadata:
  tier: 2
  owner: growth-platform
---

Dispatches order, shipping, and marketing notifications via SMS and email.

Owner: growth-platform. Tier: 2.
Depends on: twilio-sms, sendgrid-email, kafka-broker.
Depended on by: orders-service, returns-service.
Availability target: 99.5%.
Blast radius: Customers stop receiving order/shipping updates. Orders still process normally.
