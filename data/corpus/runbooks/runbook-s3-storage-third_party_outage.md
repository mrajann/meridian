---
doc_id: runbook-s3-storage-third_party_outage
doc_type: runbook
title: 's3-storage: third party outage'
services:
- s3-storage
metadata:
  root_cause_category: third_party_outage
---

s3-storage is showing requests to an external provider failing or timing out. Check the s3-storage dashboard and recent deploys via ci-pipeline before assuming the fault is in s3-storage itself.

Likely cause: the third-party provider itself is degraded, not anything on our side.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting s3-storage -- a restart will not fix third party outage if the underlying condition is still present.

Blast radius: Image loads fail; ETL and log shipping jobs stall.
