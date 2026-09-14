---
doc_id: runbook-user-profile-5xx_errors-session-store
doc_type: runbook
title: 'user-profile: 5xx errors (session-store root cause)'
services:
- user-profile
metadata:
  root_cause_category: 5xx_errors__session-store
---

user-profile is showing an elevated 5xx error rate. Check the user-profile dashboard for error rate and latency, and check recent deploys via ci-pipeline before assuming the fault is elsewhere.

Root cause: session-store is rejecting session lookups, so profile requests can't be authorized.

Fix: check session-store health directly.
