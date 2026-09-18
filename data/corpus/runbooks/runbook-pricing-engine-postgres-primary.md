---
doc_id: runbook-pricing-engine-postgres-primary
doc_type: runbook
title: 'pricing-engine: an elevated 5xx error rate (postgres-primary root cause)'
services:
- pricing-engine
metadata:
  root_cause_category: 5xx_errors__postgres-primary
---

pricing-engine is showing an elevated 5xx error rate. Check the pricing-engine dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: postgres-primary is degraded or unavailable, so pricing-engine's calls to it are failing or timing out.

Fix: check postgres-primary health directly before touching pricing-engine itself.
