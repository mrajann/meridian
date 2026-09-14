---
doc_id: runbook-voicebot-asr-rate_limit_exhaustion
doc_type: runbook
title: 'voicebot-asr: rate limit exhaustion'
services:
- voicebot-asr
metadata:
  root_cause_category: rate_limit_exhaustion
---

voicebot-asr is showing requests queueing or being rejected outright. Check llm-gateway first -- voicebot-asr depends on it directly. Check the voicebot-asr dashboard and recent deploys via ci-pipeline before assuming the fault is in voicebot-asr itself.

Likely cause: aggregate request volume exceeded the provider's quota.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting voicebot-asr -- a restart will not fix rate limit exhaustion if the underlying condition is still present.

Blast radius: Phone voicebot cannot understand callers; calls route to human agents.
