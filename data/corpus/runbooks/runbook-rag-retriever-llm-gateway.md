---
doc_id: runbook-rag-retriever-llm-gateway
doc_type: runbook
title: 'rag-retriever: requests queueing or being rejected outright (llm-gateway root
  cause)'
services:
- rag-retriever
metadata:
  root_cause_category: rate_limit_exhaustion__llm-gateway
---

rag-retriever is showing requests queueing or being rejected outright. Check the rag-retriever dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: llm-gateway is degraded or unavailable, so rag-retriever's calls to it are failing or timing out.

Fix: check llm-gateway health directly before touching rag-retriever itself.
