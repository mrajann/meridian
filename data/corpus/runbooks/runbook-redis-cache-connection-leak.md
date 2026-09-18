---
doc_id: runbook-redis-cache-connection-leak
doc_type: runbook
title: 'redis-cache: gradually increasing memory usage and periodic restarts (connection-leak
  root cause)'
services:
- redis-cache
metadata:
  root_cause_category: memory_leak__connection-leak
---

redis-cache is showing gradually increasing memory usage and periodic restarts. Check the redis-cache dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: connections are being opened but never released, so memory grows until the process restarts.

Fix: audit the connection lifecycle for a missing close/release path and patch the leak.
