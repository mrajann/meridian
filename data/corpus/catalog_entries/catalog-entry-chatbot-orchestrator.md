---
doc_id: catalog-entry-chatbot-orchestrator
doc_type: catalog_entry
title: 'Service catalog: chatbot-orchestrator'
services:
- chatbot-orchestrator
metadata:
  tier: 2
  owner: ai-platform
---

Drives the customer support chatbot's conversation and tool-use loop.

Owner: ai-platform. Tier: 2.
Depends on: llm-gateway, rag-retriever, user-profile.
Depended on by: nothing.
Availability target: 99.5%.
Blast radius: Support chatbot unavailable; customers fall back to human support.
