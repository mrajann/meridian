---
doc_id: runbook-baseline-voicebot-asr-latency_spike
doc_type: runbook
title: 'voicebot-asr: latency spike'
services:
- voicebot-asr
metadata:
  root_cause_category: latency_spike
---

voicebot-asr is showing p99 latency above its SLO target. Check llm-gateway first -- voicebot-asr depends on it directly. Check the voicebot-asr dashboard and recent deploys via ci-pipeline before assuming the fault is in voicebot-asr itself.

Likely cause: a slow query or an undersized resource pool is queueing requests.

Fix: confirm the cause above against current metrics before acting. Resolve at the source rather than restarting voicebot-asr -- a restart will not fix latency spike if the underlying condition is still present.

Blast radius: Phone voicebot cannot understand callers; calls route to human agents.
