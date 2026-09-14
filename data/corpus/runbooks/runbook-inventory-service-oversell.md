---
doc_id: runbook-inventory-service-oversell
doc_type: runbook
title: 'inventory-service: oversell risk'
services:
- inventory-service
metadata:
  root_cause_category: race_condition
---

Multiple concurrent checkouts reserved the same unit of low-stock inventory, resulting in an oversold SKU. This is almost always a race condition in the reservation logic under load, not a data corruption issue in postgres-primary.

Fix: identify the affected SKU(s) via the inventory reconciliation job, cancel or backorder the excess orders with customer support, and check whether the reservation path's row-level locking was bypassed by a recent deploy.
