---
doc_id: runbook-baseline-user-profile-5xx_errors
doc_type: runbook
title: 'user-profile: 5xx errors'
services:
- user-profile
metadata:
  root_cause_category: 5xx_errors
---

user-profile is showing an elevated 5xx error rate. Check postgres-primary first -- user-profile depends on it directly. Check the user-profile dashboard and recent deploys via ci-pipeline before assuming the fault is in user-profile itself.

Likely cause: an unhandled exception path was hit under production load that testing never exercised.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting user-profile -- a restart will not fix 5xx errors if the underlying condition is still present.

Blast radius: Customers cannot view or edit profile/address data.
