---
doc_id: runbook-sms-gateway-v1-2
doc_type: runbook
title: 'sms-gateway-v1: manual restart procedure'
services:
- sms-gateway-v1
metadata:
  root_cause_category: stale
  stale_reference: sms-gateway-v1
---

If sms-gateway-v1 shows manual restart procedure, SSH into its hosts and check the application logs directly; restart via the legacy deploy tool if needed.

[This runbook predates the migration to notification-service and was never removed. sms-gateway-v1 no longer exists.]
