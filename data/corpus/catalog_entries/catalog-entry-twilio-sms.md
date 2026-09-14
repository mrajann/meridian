---
doc_id: catalog-entry-twilio-sms
doc_type: catalog_entry
title: 'Service catalog: twilio-sms'
services:
- twilio-sms
metadata:
  tier: external
  owner: external
---

SMS delivery provider for order and shipping notifications.

Owner: external. Tier: external.
Depends on: nothing.
Depended on by: notification-service, tracking-service.
Availability target: 99.95%.
Blast radius: SMS notifications fail to send. Email notifications unaffected.
