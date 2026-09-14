---
doc_id: postmortem-secrets-manager-cert-expiry
doc_type: postmortem
title: 'Postmortem: expired certificate causes auth-service failures'
services:
- secrets-manager
- auth-service
metadata:
  root_cause_service: secrets-manager
  root_cause_category: certificate_expiry
  affected_services:
  - auth-service
  fragile_service: null
---

Summary: auth-service began rejecting all login attempts when a TLS certificate issued by secrets-manager expired without being auto-rotated.

Root cause: the certificate's auto-rotation policy was configured for a 90-day cycle, but the certificate itself was issued with only a 60-day validity, so rotation ran 30 days too late.

Action items: alert on certificate expiry directly, independent of the configured rotation cycle, and audit all other certificates issued by secrets-manager for the same mismatch.
