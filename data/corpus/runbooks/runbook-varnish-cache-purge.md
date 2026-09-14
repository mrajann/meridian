---
doc_id: runbook-varnish-cache-purge
doc_type: runbook
title: 'varnish-cache-cluster: manual cache purge'
services:
- varnish-cache-cluster
metadata:
  root_cause_category: stale_cache
  stale_reference: varnish-cache-cluster
---

If customers report seeing stale product pages, SSH into the varnish-cache-cluster nodes and run `varnishadm ban.url .` to force a full purge.

[varnish-cache-cluster was decommissioned when the storefront moved to cloudflare-cdn. Cache purges are now done through cdn-config.]
