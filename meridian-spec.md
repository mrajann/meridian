# Meridian — Incident Response Copilot
## Technical specification

**Owner:** MR
**Purpose:** Portfolio project demonstrating production-grade RAG, agentic retrieval, tool calling, multi-agent orchestration, and evaluation.
**Build method:** incremental, in Claude Code, one branch and one pull request per increment.

---

## 1. What it does

An alert fires. Four agents investigate it end to end:

1. **Triage** classifies severity and works out blast radius from the dependency graph
2. **Investigator** searches runbooks, postmortems and historical incidents to find probable root cause
3. **Escalation** decides who gets paged, how urgently, and whether the error budget justifies waking someone
4. **Comms** writes the status update for people who don't read stack traces

Output is a complete incident packet: severity, affected services, probable cause with cited evidence, recommended action, paging decision, and a customer-facing update.

**Why multiple agents is defensible here.** Each has a genuinely different objective and a different toolset. Triage reads topology. Investigator reads history. Escalation reads policy and budget. Comms writes for a non-technical audience and has no retrieval tools at all — deliberately, so it can only use what the others found. That constraint is what makes grounding measurable.

---

## 2. The fictional company — "Meridian"

Mid-size e-commerce platform. ~45 services. This is the world the corpus describes.

### Service catalog

| Layer | Services | Tier |
|---|---|---|
| **Edge** | web-frontend, mobile-api, cdn-config, api-gateway | 1 |
| **Core business** | checkout-api, orders-service, inventory-service, pricing-engine, catalog-service, cart-service | 1 |
| **Platform** | auth-service, notification-service, search-service, user-profile, session-store | 1–2 |
| **Data** | postgres-primary, postgres-replica, redis-cache, kafka-broker, warehouse-etl, analytics-api | 1–2 |
| **AI layer** | llm-gateway, chatbot-orchestrator, rag-retriever, voicebot-asr, recommendation-engine | 2 |
| **Fulfilment** | shipping-service, warehouse-api, returns-service, tracking-service | 2 |
| **Third party** | stripe-gateway, twilio-sms, sendgrid-email, s3-storage, cloudflare-cdn | external |
| **Internal** | ci-pipeline, feature-flags, config-service, secrets-manager, log-aggregator, metrics-collector | 2–3 |

### Catalog entry schema

```yaml
name: checkout-api
tier: 1
owner: payments-platform
oncall_rotation: payments-oncall
description: Order placement and payment capture. Revenue-critical path.
depends_on: [auth-service, postgres-primary, stripe-gateway, inventory-service, pricing-engine]
depended_on_by: [web-frontend, mobile-api]
slo:
  availability: 99.95
  latency_p99_ms: 400
runbooks: [checkout-5xx, checkout-latency, checkout-stripe-timeout]
blast_radius: All revenue. Complete outage means no orders can be placed.
business_hours_only: false
```

### The three deliberately fragile services

Real incident corpora are not uniformly distributed. A few services cause most of the pages. These three are the source of roughly 40% of generated incidents:

- **postgres-primary** — everything depends on it, so its failures cascade widely. Tests whether the agent correctly identifies one root cause behind many symptoms rather than reporting eight separate incidents.
- **llm-gateway** — newer, less mature, fails in ways traditional services don't (timeouts, rate limits, quality degradation without errors). Tests AI-specific reasoning.
- **notification-service** — depends on two third parties, so its failures are often somebody else's fault. Tests whether the agent correctly attributes cause to an external dependency.

---

## 3. Corpus

| Document type | Count | Role |
|---|---|---|
| Service catalog entries | 45 | Topology and ownership |
| Runbooks | 400 | Primary retrieval target |
| Postmortems | 300 | Historical correlation |
| Alert definitions | 200 | Trigger context |
| Ops chat transcripts | 150 | Noisy, realistic retrieval |
| **Total** | **~1,095 docs** | ≈ 6–8k chunks |

### Adversarial cases — build these in deliberately

The corpus is only useful if it contains the situations that break naive retrieval:

- **Near-duplicate runbooks.** `checkout-5xx-database` and `checkout-5xx-upstream` are 85% similar. Only one is right for a given alert.
- **Vocabulary mismatch.** Alert says "connection pool exhausted." Runbook says "database connections maxed out." No lexical overlap on the key term.
- **No matching runbook.** Roughly 10% of eval incidents have no correct runbook in the corpus. The agent must say so rather than retrieve the nearest thing and present it confidently. This is the single most important adversarial case.
- **Cascading failure.** One postgres-primary incident produces symptoms in six dependent services. Correct answer is one root cause, not six incidents.
- **Stale runbook.** A runbook references a service that was decommissioned. Tests whether the agent notices.

### Generation approach

Corpus is synthetic, generated from templates and the taxonomy above. Public postmortems from Cloudflare, AWS, GitHub and Google are worth reading first for structure and vocabulary — but they're copyrighted, so they inform the generator rather than appearing in the repo.

---

## 4. Evaluation

Two suites. Both run in CI.

### Labelled eval set

150 incidents, each with ground truth:

```json
{
  "incident_id": "inc-0042",
  "alert": "checkout-api p99 latency 2400ms, threshold 400ms",
  "timestamp": "2026-03-14T14:32:00Z",
  "ground_truth": {
    "severity": "SEV2",
    "root_cause_service": "postgres-primary",
    "root_cause_category": "connection_pool_exhaustion",
    "correct_runbook": "postgres-connection-pool",
    "affected_services": ["checkout-api", "orders-service", "cart-service"],
    "escalation_team": "data-platform",
    "should_page": true,
    "has_matching_runbook": true
  }
}
```

### Quantitative metrics

| Metric | What it measures |
|---|---|
| Severity accuracy | Classification against ground truth |
| Root cause service accuracy | Did it find the actual culprit |
| Root cause category accuracy | Did it classify the failure mode |
| Retrieval precision@5, recall@5, MRR | Retrieval quality |
| Escalation correctness | Right team, right urgency |
| Abstention rate | On the 10% with no matching runbook — did it correctly say "no runbook found" |
| Cascade detection | One root cause vs many symptoms |
| p50 / p95 latency | Per incident |
| Cost per incident | Token spend |

**Abstention rate is the metric worth leading with.** Most RAG demos never measure whether the system knows what it doesn't know.

### LLM-as-judge rubric — comms quality

Scored 1–5 each, on every generated status update:

1. **Customer impact stated first** — does the reader learn how they're affected before they learn about architecture
2. **Clarity to a non-engineer** — could a support lead act on this without a follow-up question
3. **Grounding** — is every factual claim traceable to retrieved evidence, or did the model invent a plausible cause
4. **Actionability** — does it say what's being done and when the next update comes
5. **Appropriate confidence** — is confirmed fact distinguished from hypothesis

Judge prompt includes the retrieved evidence, so grounding is checkable rather than guessed.

### Instruction-following evals

- **Schema compliance** — does structured output parse against the expected schema, every time
- **Refusal handling** — when evidence is insufficient, does it abstain rather than fabricate
- **Format constraints** — length limits, required sections, no internal jargon in customer-facing text

---

## 5. Agent design

### Triage Agent
**Objective:** severity and blast radius.
**Tools:** `get_service`, `get_dependencies`, `get_dependents`, `query_metrics`
**Output:** severity (SEV1–4), affected service list, blast radius statement

### Investigator Agent
**Objective:** probable root cause with evidence.
**Tools:** `search_runbooks`, `search_postmortems`, `find_similar_incidents`, `get_deploy_history`, `query_metrics`
**Output:** ranked hypotheses, each with citations. Must return "insufficient evidence" when that's true.

### Escalation Agent
**Objective:** who to page, and whether waking someone is justified.
**Tools:** `get_oncall`, `compute_error_budget`, `get_service`, `page_oncall`
**Output:** paging decision with reasoning

`compute_error_budget` is a Python port of SLO Studio's math. It links the two projects and gives the escalation decision a defensible numeric basis — a 14x burn rate justifies a 3am page; 0.4x does not.

### Comms Agent
**Objective:** customer-facing status update.
**Tools:** none, deliberately.
It receives only what the other three found. No retrieval, so it cannot introduce ungrounded claims. This is what makes the grounding score meaningful.

---

## 6. Tool layer

Real Python functions the model invokes:

```
search_runbooks(query, k=5)
search_postmortems(query, k=5)
find_similar_incidents(description, k=5)
get_service(name)
get_dependencies(name, depth=1)
get_dependents(name, depth=1)
query_metrics(service, metric, window)
get_deploy_history(service, window)
compute_error_budget(service, slo_target, window_days)
get_oncall(team)
page_oncall(team, severity, message)      # simulated
```

---

## 7. Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| LLM | Claude, Anthropic SDK |
| Embeddings | `sentence-transformers` local, swappable interface |
| Vector store | ChromaDB, persisted to disk |
| Agent core | Plain Python tool-use loop (increment 7) |
| Orchestration | LangGraph (increment 8) |
| API | FastAPI |
| UI | Streamlit |
| Evals | Custom harness, pytest-driven |
| Observability | Structured tracing, SLO metrics |
| CI | GitHub Actions — tests and evals on every push |
| Deploy | Hugging Face Spaces |

---

## 8. Build increments

One branch, one PR, one merge each. Nothing proceeds until the previous increment's tests pass.

| # | Increment | Done when |
|---|---|---|
| 1 | Repo scaffold, venv, config, `.env`, pytest, CI skeleton | `pytest` runs green in Actions |
| 2 | Service catalog + taxonomy + dependency graph | Graph traversal returns correct dependents for postgres-primary |
| 3 | Corpus generator | ~1,100 documents on disk, adversarial cases verified present |
| 4 | Chunking, embedding, Chroma indexing | Index built, similarity search returns sane results |
| 5 | Retrieval layer + **retrieval evals** | precision@5 and recall@5 measured and reported |
| 6 | Tool layer | All 11 tools unit tested |
| 7 | Single agent loop, from scratch | Agent solves an incident end to end using tools |
| 8 | Multi-agent orchestration, LangGraph | Four agents, handoffs working |
| 9 | Full eval harness — quantitative + judge | Both suites run in CI, results written to a report |
| 10 | Observability + SLO metrics | Latency, cost, and quality tracked per run |
| 11 | Streamlit UI + deploy | Public URL, working demo |

**Increment 5 is the first real checkpoint.** If retrieval quality is poor there, everything downstream inherits the problem. Do not skip past it because the agent work is more interesting.

---

## 9. Open items — easily changed later

- Service count could go to 60+ if the dependency graph feels thin
- Judge could be swapped to a different model than the generator, which is better practice and worth testing
- Corpus could add a second company for domain-transfer testing
- LangGraph could be replaced with plain orchestration if it adds more ceremony than value
