---
doc_id: postmortem-rag-retriever-rate_limit_exhaustion
doc_type: postmortem
title: 'Postmortem: rag-retriever rate limit exhaustion'
services:
- rag-retriever
metadata:
  root_cause_service: rag-retriever
  root_cause_category: rate_limit_exhaustion
  affected_services: []
  fragile_service: null
---

Summary: rag-retriever experienced requests queueing or being rejected outright.

Root cause: aggregate request volume exceeded the provider's quota.

Action items: add direct alerting on this failure mode for rag-retriever rather than relying on downstream symptoms to surface it.
