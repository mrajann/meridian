---
doc_id: runbook-stale-varnish-cache-cluster-2
doc_type: runbook
title: 'varnish-cache-cluster: elevated error rate'
services:
- varnish-cache-cluster
metadata:
  root_cause_category: stale
  stale_reference: varnish-cache-cluster
  adversarial_case: stale_runbook
---

If varnish-cache-cluster shows elevated error rate, SSH into its hosts and check the application logs directly; restart via the legacy deploy tool if needed.

[This runbook references a decommissioned service. varnish-cache-cluster no longer exists in the current catalog.]
