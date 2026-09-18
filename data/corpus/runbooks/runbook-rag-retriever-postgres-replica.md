---
doc_id: runbook-rag-retriever-postgres-replica
doc_type: runbook
title: 'rag-retriever: requests queueing or being rejected outright (postgres-replica
  root cause)'
services:
- rag-retriever
metadata:
  root_cause_category: rate_limit_exhaustion__postgres-replica
---

rag-retriever is showing requests queueing or being rejected outright. Check the rag-retriever dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-replica is degraded or unavailable, so rag-retriever's calls to it are failing or timing out.

Fix: check postgres-replica health directly before touching rag-retriever itself.
