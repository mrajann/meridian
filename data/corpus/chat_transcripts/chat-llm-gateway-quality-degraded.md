---
doc_id: chat-llm-gateway-quality-degraded
doc_type: chat_transcript
title: '#support-eng: chatbot answers feel off'
services:
- llm-gateway
- chatbot-orchestrator
metadata:
  root_cause_service: llm-gateway
---

[09:14] @sam: support lead says chatbot answers have felt off since this morning
[09:15] @jules: no alerts firing though, error rate and latency both look normal
[09:16] @sam: could be rag-retriever returning bad context?
[09:20] @jules: checked, retrieval results look fine and relevant
[09:24] @sam: quality score dashboard actually is way down, just no alert threshold on it
[09:25] @jules: checking llm-gateway routing config... there was a routing change at 07:00
[09:26] @jules: rolling back the routing change now
[09:35] @sam: quality score climbing back up, looks like that was it
