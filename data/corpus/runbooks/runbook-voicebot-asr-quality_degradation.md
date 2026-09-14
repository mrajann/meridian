---
doc_id: runbook-voicebot-asr-quality_degradation
doc_type: runbook
title: 'voicebot-asr: quality degradation'
services:
- voicebot-asr
metadata:
  root_cause_category: quality_degradation
---

voicebot-asr is showing output quality dropping with no traditional error signal. Check llm-gateway first -- voicebot-asr depends on it directly. Check the voicebot-asr dashboard and recent deploys via ci-pipeline before assuming the fault is in voicebot-asr itself.

Likely cause: a routing or model-version change degraded output quality without tripping a health check.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting voicebot-asr -- a restart will not fix quality degradation if the underlying condition is still present.

Blast radius: Phone voicebot cannot understand callers; calls route to human agents.
