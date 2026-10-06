# Five-minute demo guide

Use this as a short recording outline. The web preview is suitable for recording from the Replit workspace; publish first if the reviewer needs to open it without Replit access.

1. **0:00–0:30 — Introduce the product.** Explain that Reply Desk helps an agent answer a customer while keeping the brand's own policy visible.
2. **0:30–1:10 — Show the conversation.** Point out customer, brand, message history and order details. Switch to Customer, send a follow-up, then switch back to Agent.
3. **1:10–2:10 — Generate and review.** Generate a reply. Show the retrieved damaged-item policy, match level and review notice. Edit the response, save the edit, then approve and send it.
4. **2:10–2:50 — Demonstrate brand isolation.** Switch to Tide & Timber. Show its distinct damaged-item rule. Open the Knowledge Base, edit or add an entry, return to Inbox and regenerate to show the change is manageable in the app.
5. **2:50–3:30 — Show the guardrail.** Add a message with a policy topic not covered by the selected brand. The assistant should indicate no matching policy and ask the agent to verify rather than inventing an answer.
6. **3:30–4:20 — Explain engineering choices.** Demo mode is local and grounded; a live OpenRouter provider is optional. Explain that the app logs context, draft, edit, final response and timestamp.
7. **4:20–5:00 — Explain the architecture and next improvement.** Show the diagram and discuss tenant checks, durable webhook/outbound queues, and evaluation. A good next improvement is auth plus PostgreSQL RLS and integration tests for cross-brand isolation.

Speak only to what the app currently does. Do not describe demo mode as a live LLM call. If a live model secret is configured, show the provider line in AI activity.
