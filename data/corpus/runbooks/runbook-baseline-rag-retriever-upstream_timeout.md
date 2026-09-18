---
doc_id: runbook-baseline-rag-retriever-upstream_timeout
doc_type: runbook
title: 'rag-retriever: upstream timeout'
services:
- rag-retriever
metadata:
  root_cause_category: upstream_timeout
---

rag-retriever is showing elevated latency or errors tracing to one specific upstream call. Check llm-gateway first -- rag-retriever depends on it directly. Check the rag-retriever dashboard and recent deploys via ci-pipeline before assuming the fault is in rag-retriever itself.

Likely cause: a synchronous call to a slow or degraded upstream is blocking the request path.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting rag-retriever -- a restart will not fix upstream timeout if the underlying condition is still present.

Blast radius: Chatbot answers lose grounding and become less accurate. Chatbot stays up.
