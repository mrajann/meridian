---
doc_id: catalog-entry-llm-gateway
doc_type: catalog_entry
title: 'Service catalog: llm-gateway'
services:
- llm-gateway
metadata:
  tier: 2
  owner: ai-platform
---

Internal proxy to external LLM providers: routing, key management, rate limiting.

Owner: ai-platform. Tier: 2.
Depends on: secrets-manager, feature-flags.
Depended on by: chatbot-orchestrator, rag-retriever, recommendation-engine, voicebot-asr.
Availability target: 99.5%.
Blast radius: All AI-layer features (chatbot, voicebot, recommendations, RAG) degrade or fail.
