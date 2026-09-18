---
doc_id: runbook-cascade-root-cause-pricing-engine-race_condition
doc_type: runbook
title: 'pricing-engine: inconsistent or duplicated state under concurrent load (cascading)'
services:
- pricing-engine
metadata:
  root_cause_category: race_condition
---

pricing-engine is showing inconsistent or duplicated state under concurrent load. Because so many services depend on pricing-engine directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single pricing-engine alert -- treat a burst of simultaneous cross-service errors as one pricing-engine incident, not several.

Root cause: two concurrent operations both read stale state before either write committed.

Fix: resolve the condition on pricing-engine directly; the downstream services will recover on their own once it does.
