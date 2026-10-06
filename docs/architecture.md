# Scalable CX Reply Platform

## Architecture

The agent console is a React web application served behind an API gateway. Agents authenticate with an OIDC provider and receive short-lived tokens containing their user identity and authorized brand memberships. Every request enters through a tenant resolver that validates the token and selects an allowed `brand_id`; clients cannot choose an arbitrary tenant. The conversation API reads and writes PostgreSQL records through brand-scoped repositories. PostgreSQL is the source of truth for customers, orders, conversations, messages, policies, audit events and delivery state.

Inbound WhatsApp, email and commerce events arrive at channel-specific webhook adapters. The adapter verifies signatures, normalizes the event, and writes it plus an outbox record in one transaction. A unique `(channel, provider_event_id)` constraint makes duplicate deliveries safe. Queue workers process the outbox, enrich the conversation with authorized order data, store the inbound message and emit an event for the agent console. Outbound messages use the same durable outbox pattern so a process crash cannot lose a reply after it is approved.

Knowledge policies are managed in PostgreSQL. An indexing worker creates embeddings and upserts policy chunks into Qdrant with mandatory metadata: `brand_id`, policy ID, locale, effective version and status. At reply time, retrieval applies the authenticated brand filter before ranking, then checks that returned policy IDs are active and belong to the same brand in PostgreSQL. For a small policy set, PostgreSQL full-text or lexical search is a simpler starting point; add Qdrant when relevance evaluations show that semantic retrieval improves results.

The AI gateway receives only the latest relevant conversation turns, authorized order facts and retrieved policy excerpts. It applies prompt templates with version IDs, redacts unnecessary personal data, selects a model by task and budget, limits context/output tokens, and records latency, token use and model cost. The assessment demo uses a conservative validator that blocks direct refund/replacement promises unless a policy explicitly authorizes them; a production validator should be broader and tested against a versioned support-case set. Low retrieval coverage, policy conflict, timeout, or validation failure produces a clearly marked human-review fallback, not a confident promise. Agents can edit, regenerate, approve or send a manual message.

## Diagram

See [`architecture-diagram.svg`](architecture-diagram.svg). It shows the interactive path, background path, data stores and tenant-boundary checks.

## Brand isolation

Isolation is enforced at multiple layers, not by relying on a UI filter:

1. Identity membership is checked server-side for every requested brand. Authorization derives from verified claims and membership records, not a `brand_id` supplied by the browser.
2. The backend requires a brand-scoped repository method. Tables include `brand_id`; important relationships use composite foreign keys such as `(brand_id, conversation_id)` so a row cannot reference a conversation in another brand.
3. PostgreSQL row-level security is enabled on tenant tables. Each transaction sets the authenticated brand in a transaction-local setting; policies deny access when it is missing. Cross-brand administrative jobs use a separate audited role.
4. Qdrant search always includes a server-built `brand_id` filter. The tenant value is not accepted from model output or user text. Results are revalidated against the relational source of truth.
5. Cache keys, job payloads, event topics and idempotency keys include the tenant scope. Automated tests attempt cross-brand reads, writes, retrieval and cache collisions and must fail closed.

## Reliability and scale

At 500 brands, the first limits are likely to be database connection/query pressure, webhook fan-out and model rate limits rather than raw web request serving. Add connection pooling, composite indexes beginning with `brand_id`, read replicas for suitable reads, queue-backed webhook processing, and worker autoscaling by queue age. Track queue lag and per-brand quotas so one busy customer cannot starve others. Move message history to time partitions only after measured table size and retention needs justify it. Shard Qdrant by workload or tenant tier only when shared filtered collections stop meeting latency and isolation requirements.

Webhook delivery is at-least-once: persist provider event IDs under a unique key and return success for a previously processed event. External API calls use bounded timeouts, exponential backoff with jitter, circuit breakers and a dead-letter queue for exhausted retries. AI calls have a short retry budget; if they still fail, preserve the conversation and offer an agent a manual reply path. For sending, commit the approved response and outbox record atomically, then let a worker deliver it. Track states such as `pending`, `sent`, `failed` and `unknown`; use provider idempotency keys where available and reconcile uncertain outcomes rather than blindly resending.

Measure success and reliability by brand and channel: ingestion delay, queue age, retrieval hit rate, human edit/approval rate, policy citation coverage, unsupported-claim rate, model latency, token/cost per resolved conversation, delivery failure rate and fallback rate. Keep prompt, model and knowledge versions with each run so regressions can be replayed.

## Demo trade-offs

The assessment app uses Python's standard library, SQLite and lexical retrieval so it starts without a package install or external credentials. Its two sample brands demonstrate that conversation retrieval is brand-scoped. It has no authentication and is not safe for real customer data. In production I would move to PostgreSQL with enforced RLS, add authenticated brand memberships and durable queues, and evaluate retrieval/model changes against a versioned support-case test set before rollout.
