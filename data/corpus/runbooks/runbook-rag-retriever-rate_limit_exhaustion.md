---
doc_id: runbook-rag-retriever-rate_limit_exhaustion
doc_type: runbook
title: 'rag-retriever: rate limit exhaustion'
services:
- rag-retriever
metadata:
  root_cause_category: rate_limit_exhaustion
---

rag-retriever is showing requests queueing or being rejected outright. Check llm-gateway first -- rag-retriever depends on it directly. Check the rag-retriever dashboard and recent deploys via ci-pipeline before assuming the fault is in rag-retriever itself.

Likely cause: aggregate request volume exceeded the provider's quota.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting rag-retriever -- a restart will not fix rate limit exhaustion if the underlying condition is still present.

Blast radius: Chatbot answers lose grounding and become less accurate. Chatbot stays up.
