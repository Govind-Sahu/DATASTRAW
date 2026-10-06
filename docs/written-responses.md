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

I help junior teammates with technical problem solving. To make this answer specific, I still need one real example: what problem the teammate was solving, what help I gave, and what happened afterward. I should describe my role accurately and not imply that I formally managed the teammate if I did not.

### 2. Giving feedback

I would make the feedback specific to the code and its impact, not the developer's character. Since we have already discussed the pattern once, I would ask what is making the structure difficult, then look at a recent example together. I would agree on a small set of concrete expectations—such as clear boundaries, naming and tests—and pair on refactoring one representative piece. I would follow up on the next change, recognize improvement, and be clear if the same issue continues. The aim is to help them build judgment, not just rewrite their code for them.

### 3. Disagreement

I would ask them to explain the risks or evidence behind their view and make sure I understand it before defending my choice. I would compare the options against agreed goals such as reliability, delivery time, cost and reversibility. If the decision is reversible, I would time-box a small experiment or prototype. If a decision is needed before we can test, I would make the trade-off and rationale explicit, invite dissent, and document the outcome. After the decision, I would support the team in executing it and revisit it if new evidence appears.

### 4. Mistake and ownership

In one project, I made a mistake while writing a database query for a report. I missed a required condition, so the report returned more records than the business expected. We caught it during testing by comparing the output with the expected business data. I took ownership, reviewed the SQL against the requirement, identified the missing condition and corrected the query. I informed the senior developer about the issue and the fix. Then I tested different data scenarios, including records that should be included and excluded, and compared the results with what we expected.

Because the issue was found before production, its impact remained within testing. Afterward, I became more deliberate about checking report queries against the business requirements, testing edge cases and validating sample results before I considered the work ready for final review. The experience taught me that code can run correctly while still answering the wrong business question. I treat checking the output against the expected business result as part of implementation, and I communicate mistakes early rather than only correcting them quietly.

### 5. Joining Datastraw: first 30 days

In the first week, I would listen and map the product, customers, current architecture, integrations, operational risks and team expectations. I would ask people who handle support and operations where failures or repeated work are most costly, and review existing incidents and deployment practices.

In weeks two and three, I would trace a few important workflows end to end, identify owners and undocumented assumptions, and write down the highest-risk gaps. I would avoid a broad rewrite before understanding why the current processes exist. I would choose one small improvement with a clear user or reliability benefit and agree on how we will measure it.

By day 30, I would share a short, prioritized view of what I learned, what should be fixed now, what can wait and where more evidence is needed. I would establish lightweight habits with the team—clear ownership, reviewable changes, incident notes and useful documentation—without adding process for its own sake.

## AI usage disclosure for the assessment

This assessment app and draft materials were built with **Replit Agent** in the Replit workspace. It helped interpret the assignment, implement the UI and server, and draft technical documentation. I reviewed the generated code and tested the core flows rather than treating generated output as verified.

During development, Replit Agent introduced an HTTP error-handler method that called itself recursively. That method was removed before the final app run and tests. The project's package installer also failed before dependencies could be installed, so the app was implemented with the Python standard library instead of adding an unverified dependency.

Before submitting, I will make sure I can explain the retrieval trade-off, how the app scopes policy lookup to a brand, what the demo mode does, and what I would change for production.
