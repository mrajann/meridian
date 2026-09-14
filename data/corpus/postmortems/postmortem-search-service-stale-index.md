---
doc_id: postmortem-search-service-stale-index
doc_type: postmortem
title: 'Postmortem: search-service stale index causing zero results'
services:
- search-service
metadata:
  root_cause_service: search-service
  root_cause_category: stale_index
  affected_services: []
  fragile_service: null
---

Summary: the nightly search index rebuild silently failed for three consecutive nights, so newly-added product terms returned zero results even though the products existed in catalog-service.

Root cause: the index rebuild job swallowed an exception instead of failing loudly, so no alert fired on the job itself -- the only signal was the customer-facing symptom.

Note: no runbook existed for 'search returns zero results with no errors' at the time of this incident -- the on-call engineer spent the first 40 minutes checking search-service-5xx, which does not apply here since no errors were being thrown. Action items: write a dedicated runbook for this failure mode, and alert on index rebuild job failure directly.
