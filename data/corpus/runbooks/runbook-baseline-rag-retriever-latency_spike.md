---
doc_id: runbook-baseline-rag-retriever-latency_spike
doc_type: runbook
title: 'rag-retriever: latency spike'
services:
- rag-retriever
metadata:
  root_cause_category: latency_spike
---

rag-retriever is showing p99 latency above its SLO target. Check llm-gateway first -- rag-retriever depends on it directly. Check the rag-retriever dashboard and recent deploys via ci-pipeline before assuming the fault is in rag-retriever itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting rag-retriever -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Chatbot answers lose grounding and become less accurate. Chatbot stays up.
