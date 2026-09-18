---
doc_id: runbook-baseline-voicebot-asr-upstream_timeout
doc_type: runbook
title: 'voicebot-asr: upstream timeout'
services:
- voicebot-asr
metadata:
  root_cause_category: upstream_timeout
---

voicebot-asr is showing elevated latency or errors tracing to one specific upstream call. Check llm-gateway first -- voicebot-asr depends on it directly. Check the voicebot-asr dashboard and recent deploys via ci-pipeline before assuming the fault is in voicebot-asr itself.

Likely cause: a synchronous call to a slow or degraded upstream is blocking the request path.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting voicebot-asr -- a restart will not fix upstream timeout if the underlying condition is still present.

Blast radius: Phone voicebot cannot understand callers; calls route to human agents.
