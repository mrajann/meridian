---
doc_id: postmortem-session-store-eviction-storm
doc_type: postmortem
title: 'Postmortem: session-store eviction storm forces mass logout'
services:
- session-store
- redis-cache
metadata:
  root_cause_service: session-store
  root_cause_category: cache_eviction
  affected_services:
  - user-profile
  fragile_service: null
---

Summary: a memory limit change on the underlying redis-cache instance triggered an eviction storm on session-store, logging out a large fraction of active users simultaneously.

Root cause: session-store shares its redis-cache instance with other cache consumers, and a routine memory limit reduction did not account for session-store's actual working set size.

Action items: give session-store a dedicated redis-cache instance rather than sharing capacity with lower-priority cache consumers.
