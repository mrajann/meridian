---
doc_id: runbook-postgres-primary-disk-full
doc_type: runbook
title: 'postgres-primary: disk full'
services:
- postgres-primary
metadata:
  root_cause_category: disk_full
---

postgres-primary is refusing writes or has stopped accepting new connections, and every service that depends on it -- directly or transitively -- starts erroring at once. Check disk usage on the primary before anything else: `df -h` on the data volume. WAL buildup from a stalled replica or an oversized unvacuumed table are the two most common causes.

Fix: free space immediately (rotate/ship old WAL segments, drop temp tables) to restore write capacity, then find the actual growth source before it recurs. Do not restart postgres-primary to 'fix' disk-full -- that does not free space and adds a recovery window on top of the outage.

This will present as simultaneous 5xx alerts across checkout-api, orders-service, auth-service, and several other unrelated-looking services -- treat it as one incident, not one per service.
