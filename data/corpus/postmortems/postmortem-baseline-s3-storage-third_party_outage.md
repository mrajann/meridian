---
doc_id: postmortem-baseline-s3-storage-third_party_outage
doc_type: postmortem
title: 'Postmortem: s3-storage third party outage'
services:
- s3-storage
metadata:
  root_cause_service: s3-storage
  root_cause_category: third_party_outage
  affected_services: []
  fragile_service: null
---

Summary: s3-storage experienced requests to an external provider failing or timing out.

Root cause: the third-party provider itself is degraded, not anything on our side.

Action items: add direct alerting on this failure mode for s3-storage rather than relying on downstream symptoms to surface it.
