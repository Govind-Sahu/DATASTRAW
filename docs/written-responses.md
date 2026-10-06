# Written Responses — Parts 3 and 4

**Candidate:** [Your name]

> Before submitting: replace the bracketed personal-experience prompts with true examples. Do not claim leadership, incidents or responsibilities you did not have. Read the technical answers and make sure you can explain them in a discussion.

## Part 3 — Technical Problem Solving

### AI costs increased from ₹20k to ₹1 lakh while customers and conversations grew about 40%. What would you investigate and change?

I would first reconcile the cost data with provider invoices, including model, token, retry and billing changes. A five-fold cost increase with about 1.4× the conversation volume implies roughly 3.6× higher cost per conversation, so I would look for a change in unit cost rather than assume traffic alone explains it.

I would compare the last three months by model and task: calls per conversation, input/output tokens, p50/p95 prompt size, model price, retries/timeouts, regeneration rate, and cost per resolved conversation. I would check deployments for a model change, longer conversation history, duplicated tool calls, retrieval returning too many chunks, prompt growth, failed calls billed before retry, and automation triggering AI on messages that do not need it. I would also check whether reporting uses consistent currency, credits and time windows, and identify the tenants or workflows driving the increase.

I would make low-risk changes first: set per-brand budgets and alerts; cap prompt history and output tokens; send only relevant, versioned policy excerpts; use a lower-cost model for routine classification or low-risk drafts and reserve stronger models for cases that need them; avoid calling a model for deterministic workflows; and apply carefully scoped caching to stable policy answers. Cache keys must include brand, locale and policy version so one brand can never receive another brand's answer. I would cap retries, add a human-review fallback, and evaluate quality before routing more traffic to a cheaper model.

I would track cost per conversation and per resolved conversation alongside latency, retrieval relevance, agent edits, approval rate and unsupported-claim rate. I would roll changes out gradually by tenant or a small traffic percentage, compare against a versioned evaluation set, and roll back if quality or safety worsens. Rate limits and alerts help contain another spike, but they do not replace finding its cause.

## Part 4 — Leadership and Ownership

### 1. Leadership

**Personalize this answer with one truthful path.**

- If you have led or mentored someone: “I supported [number] [role/experience level] teammate(s) for [duration]. I was responsible for [specific work: onboarding, reviews, pairing, planning or unblockers]. The hardest part was [real challenge]. I handled it by [specific action] and learned [lesson].”
- If you have not formally led someone: “I have not formally managed a teammate. One situation where I helped someone less experienced was [real situation]. I [specific action], and the result was [observable result]. It taught me [lesson about support or communication].”

### 2. Giving feedback

I would make the feedback specific to the code and its impact, not the developer's character. Since we have already discussed the pattern once, I would ask what is making the structure difficult, then look at a recent example together. I would agree on a small set of concrete expectations—such as clear boundaries, naming and tests—and pair on refactoring one representative piece. I would follow up on the next change, recognize improvement, and be clear if the same issue continues. The aim is to help them build judgment, not just rewrite their code for them.

### 3. Disagreement

I would ask them to explain the risks or evidence behind their view and make sure I understand it before defending my choice. I would compare the options against agreed goals such as reliability, delivery time, cost and reversibility. If the decision is reversible, I would time-box a small experiment or prototype. If a decision is needed before we can test, I would make the trade-off and rationale explicit, invite dissent, and document the outcome. After the decision, I would support the team in executing it and revisit it if new evidence appears.

### 4. Mistake and ownership

**Replace this scaffold with a real incident you can discuss. Keep the facts and impact accurate.**

“I [specific mistake] while working on [system or task]. It affected [person, customer or business outcome] by [concrete impact]. When I realized it, I [immediate mitigation and who you informed]. I then [root-cause fix or recovery], and followed up by [prevention, monitoring, test, documentation or process change]. I learned [specific lesson].”

Do not invent a production outage if the real example was smaller. A contained mistake with clear ownership and learning is stronger than an exaggerated story.

### 5. Joining Datastraw: first 30 days

In the first week, I would listen and map the product, customers, current architecture, integrations, operational risks and team expectations. I would ask people who handle support and operations where failures or repeated work are most costly, and review existing incidents and deployment practices.

In weeks two and three, I would trace a few important workflows end to end, identify owners and undocumented assumptions, and write down the highest-risk gaps. I would avoid a broad rewrite before understanding why the current processes exist. I would choose one small improvement with a clear user or reliability benefit and agree on how we will measure it.

By day 30, I would share a short, prioritized view of what I learned, what should be fixed now, what can wait and where more evidence is needed. I would establish lightweight habits with the team—clear ownership, reviewable changes, incident notes and useful documentation—without adding process for its own sake.

## AI usage disclosure for the assessment

This assessment app and draft materials were built with **Replit Agent** in the Replit workspace. It helped interpret the assignment, implement the UI and server, and draft technical documentation. I reviewed the generated code and tested the core flows rather than treating generated output as verified.

One incorrect suggestion was an HTTP error-handler method that called itself recursively. I spotted it while reviewing the server implementation and removed it before running the app. I also chose a standard-library implementation after the project package installer failed, rather than adding a dependency that I could not install and verify.

Before submitting, I will make sure I can explain the retrieval trade-off, how the app scopes policy lookup to a brand, what the demo mode does, and what I would change for production.
