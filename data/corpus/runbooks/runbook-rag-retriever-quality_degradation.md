---
doc_id: runbook-rag-retriever-quality_degradation
doc_type: runbook
title: 'rag-retriever: quality degradation'
services:
- rag-retriever
metadata:
  root_cause_category: quality_degradation
---

rag-retriever is showing output quality dropping with no traditional error signal. Check llm-gateway first -- rag-retriever depends on it directly. Check the rag-retriever dashboard and recent deploys via ci-pipeline before assuming the fault is in rag-retriever itself.

Likely cause: a routing or model-version change degraded output quality without tripping a health check.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting rag-retriever -- a restart will not fix quality degradation if the underlying condition is still present.

Blast radius: Chatbot answers lose grounding and become less accurate. Chatbot stays up.
