---
doc_id: postmortem-api-gateway-rate-limit-misconfig
doc_type: postmortem
title: 'Postmortem: api-gateway rate limit blocks legitimate traffic'
services:
- api-gateway
metadata:
  root_cause_service: api-gateway
  root_cause_category: misconfiguration
  affected_services:
  - web-frontend
  - mobile-api
  fragile_service: null
---

Summary: a rate-limit config change intended to target a single abusive IP range instead matched a much broader CIDR block, blocking a portion of legitimate customer traffic.

Root cause: the CIDR block in the rate-limit rule was copied from an incident runbook example rather than the actual abusive range identified in that incident.

Action items: require a dry-run mode for rate-limit rule changes that reports matched traffic volume before the rule goes live.
