---
doc_id: runbook-baseline-twilio-sms-third_party_outage
doc_type: runbook
title: 'twilio-sms: third party outage'
services:
- twilio-sms
metadata:
  root_cause_category: third_party_outage
---

twilio-sms is showing requests to an external provider failing or timing out. Check the twilio-sms dashboard and recent deploys via ci-pipeline before assuming the fault is in twilio-sms itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting twilio-sms -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: SMS notifications fail to send. Email notifications unaffected.
