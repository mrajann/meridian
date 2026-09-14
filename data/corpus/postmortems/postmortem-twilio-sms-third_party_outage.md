---
doc_id: postmortem-twilio-sms-third_party_outage
doc_type: postmortem
title: 'Postmortem: twilio-sms third party outage'
services:
- twilio-sms
metadata:
  root_cause_service: twilio-sms
  root_cause_category: third_party_outage
  affected_services: []
  fragile_service: null
---

Summary: twilio-sms experienced requests to an external provider failing or timing out.

Root cause: the third-party provider itself is degraded, not anything on our side.

Action items: add direct alerting on this failure mode for twilio-sms rather than relying on downstream symptoms to surface it.
