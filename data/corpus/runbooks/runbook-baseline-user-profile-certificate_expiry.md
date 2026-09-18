---
doc_id: runbook-baseline-user-profile-certificate_expiry
doc_type: runbook
title: 'user-profile: certificate expiry'
services:
- user-profile
metadata:
  root_cause_category: certificate_expiry
---

user-profile is showing auth or TLS failures with no code change involved. Check postgres-primary first -- user-profile depends on it directly. Check the user-profile dashboard and recent deploys via ci-pipeline before assuming the fault is in user-profile itself.

Likely cause: a certificate expired without being auto-rotated in time.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting user-profile -- a restart will not fix certificate expiry if the underlying condition is still present.

Blast radius: Customers cannot view or edit profile/address data.
