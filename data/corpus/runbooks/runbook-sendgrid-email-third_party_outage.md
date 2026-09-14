---
doc_id: runbook-sendgrid-email-third_party_outage
doc_type: runbook
title: 'sendgrid-email: third party outage'
services:
- sendgrid-email
metadata:
  root_cause_category: third_party_outage
---

sendgrid-email is showing requests to an external provider failing or timing out. Check the sendgrid-email dashboard and recent deploys via ci-pipeline before assuming the fault is in sendgrid-email itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting sendgrid-email -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: Email notifications fail to send. SMS notifications unaffected.
