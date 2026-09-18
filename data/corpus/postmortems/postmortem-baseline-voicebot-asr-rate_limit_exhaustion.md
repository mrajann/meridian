---
doc_id: postmortem-baseline-voicebot-asr-rate_limit_exhaustion
doc_type: postmortem
title: 'Postmortem: voicebot-asr rate limit exhaustion'
services:
- voicebot-asr
metadata:
  root_cause_service: voicebot-asr
  root_cause_category: rate_limit_exhaustion
  affected_services: []
  fragile_service: null
---

Summary: voicebot-asr experienced requests queueing or being rejected outright.

Root cause: aggregate request volume exceeded the provider's quota.

Action items: add direct alerting on this failure mode for voicebot-asr rather than relying on downstream symptoms to surface it.
