---
doc_id: runbook-llm-gateway-upstream_timeout-secrets-manager
doc_type: runbook
title: 'llm-gateway: upstream timeout (secrets-manager root cause)'
services:
- llm-gateway
metadata:
  root_cause_category: upstream_timeout__secrets-manager
---

llm-gateway is showing elevated latency or errors tracing to one specific upstream call. Check the llm-gateway dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: secrets-manager failed to rotate the provider API key in time, so requests are being rejected with auth errors.

Fix: check secrets-manager for the provider key's rotation status and rotate manually if it's expired.
