---
doc_id: runbook-warehouse-mainframe-v1-1
doc_type: runbook
title: 'warehouse-mainframe-v1: elevated error rate'
services:
- warehouse-mainframe-v1
metadata:
  root_cause_category: stale
  stale_reference: warehouse-mainframe-v1
---

If warehouse-mainframe-v1 shows elevated error rate, SSH into its hosts and check the application logs directly; restart via the legacy deploy tool if needed.

[This runbook predates the migration to warehouse-api and was never removed. warehouse-mainframe-v1 no longer exists.]
