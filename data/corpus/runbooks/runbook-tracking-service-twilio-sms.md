---
doc_id: runbook-tracking-service-twilio-sms
doc_type: runbook
title: 'tracking-service: an elevated 5xx error rate (twilio-sms root cause)'
services:
- tracking-service
metadata:
  root_cause_category: 5xx_errors__twilio-sms
---

tracking-service is showing an elevated 5xx error rate. Check the tracking-service dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: twilio-sms is degraded or unavailable, so tracking-service's calls to it are failing or timing out.

Fix: check twilio-sms health directly before touching tracking-service itself.
