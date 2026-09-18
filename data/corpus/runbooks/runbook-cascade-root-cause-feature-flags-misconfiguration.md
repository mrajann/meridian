---
doc_id: runbook-cascade-root-cause-feature-flags-misconfiguration
doc_type: runbook
title: 'feature-flags: unexpected behavior with no code change involved (cascading)'
services:
- feature-flags
metadata:
  root_cause_category: misconfiguration
---

feature-flags is showing unexpected behavior with no code change involved. Because so many services depend on feature-flags directly or transitively, this often presents as simultaneous errors across several unrelated-looking services rather than a single feature-flags alert -- treat a burst of simultaneous cross-service errors as one feature-flags incident, not several.

Root cause: a configuration change had a broader blast radius than intended.

Fix: resolve the condition on feature-flags directly; the downstream services will recover on their own once it does.
