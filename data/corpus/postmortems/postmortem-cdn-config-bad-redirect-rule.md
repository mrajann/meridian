---
doc_id: postmortem-cdn-config-bad-redirect-rule
doc_type: postmortem
title: 'Postmortem: cdn-config bad redirect rule causes 404s'
services:
- cdn-config
- cloudflare-cdn
metadata:
  root_cause_service: cdn-config
  root_cause_category: misconfiguration
  affected_services:
  - web-frontend
  fragile_service: null
---

Summary: a redirect rule pushed to cloudflare-cdn to deprecate an old URL pattern had an overly broad regex, causing 404s for a set of currently-valid product URLs.

Root cause: the regex was tested against a handful of sample URLs but not against the full corpus of currently-active product URL patterns.

Action items: require redirect rule changes to run against a sample of live traffic in a shadow mode before taking effect.
