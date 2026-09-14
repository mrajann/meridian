---
doc_id: runbook-legacy-monolith-5xx
doc_type: runbook
title: 'checkout-monolith-v1: elevated error rate'
services:
- checkout-monolith-v1
metadata:
  root_cause_category: 5xx_errors
  stale_reference: checkout-monolith-v1
---

checkout-monolith-v1 is returning elevated 5xx rates. Check the monolith's application server logs on the checkout-monolith-v1 hosts and restart the affected instances via the legacy deploy tool.

[This runbook predates the 2024 migration to checkout-api and was never removed. checkout-monolith-v1 no longer exists.]
