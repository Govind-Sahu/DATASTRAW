# Reply Desk — Datastraw CX Assistant

A small, runnable support-reply assistant built for the Datastraw hiring assessment. It demonstrates a customer conversation loop, brand-specific policy management and retrieval, draft review, and an audit trail.

## Run in Replit

1. Open this repl and press **Run**. The app uses the existing Python runtime and Python's standard library; it does not need package installation.
2. Open the web preview. The first run seeds two fictional brands and conversations into `instance/cx_assistant.sqlite`.
3. In Inbox, choose a brand and conversation. Switch between **Agent** and **Customer** to add messages from either side.
4. As Agent, click **Generate reply**. Review the retrieved context and suggested response, edit it, save the edit if useful, then approve and send. A manual reply can also be sent without generating an AI draft.
5. Open **Knowledge base** to add, edit, or delete policy entries for either brand. Regenerate to verify that retrieval changes with the saved policy.
6. Open **AI activity** to review the customer message, retrieved context, generated draft, edited response, final response, provider and timestamp.

## Run locally

1. Extract the project ZIP and open a terminal in the folder containing `main.py`.
2. Install Python 3.10 or newer if it is not already installed. No `pip install` is needed; the app uses the Python standard library.
3. Start the server:
   - Windows: `py main.py`
   - macOS/Linux: `python3 main.py`
4. Open `http://127.0.0.1:5000` in a browser. Press `Ctrl+C` in the terminal to stop the server.

The first run creates `instance/cx_assistant.sqlite` with fictional demo data. Without an OpenRouter key, the app stays in Grounded demo mode.

## AI provider

The app works immediately in **Grounded demo mode** using a small deterministic, policy-aware draft generator. This is intentional: no model credentials are bundled, and the interface labels this mode rather than claiming a live model was called.

To enable live generation:

1. Add `OPENROUTER_API_KEY` as a Replit Secret (never commit it or paste it into source code).
2. Optionally set `OPENROUTER_MODEL`; it defaults to `openai/gpt-4o-mini`.
3. Restart the app. The server sends only the latest customer message and retrieved entries belonging to that conversation's brand to the model.

If the configured model request fails, the app reports the failure and stores a failed run; it does not quietly present the local fallback as an LLM response. The grounded fallback is placed in the manual composer for agent review and is labeled separately in the activity log.

## Architecture and scope

- **Runtime:** Python standard library HTTP server, SQLite, static HTML/CSS/JavaScript.
- **Persistence:** `instance/cx_assistant.sqlite`; tables and indexes are initialized on startup. Seed data is inserted only into an empty brand table.
- **Retrieval:** lightweight lexical scoring for this small policy set. The query always filters entries by the conversation's `brand_id`; the model never receives another brand's knowledge.
- **Guardrails:** model prompts require grounding and prohibit unsupported guarantees. A conservative validator blocks direct refund/replacement promises unless a policy explicitly authorizes them. The local demo draft uses retrieved policy information and escalates when no relevant policy exists. Agents must review before sending.
- **Audit:** each AI run stores its source message, retrieved context, generated response, agent edit, final sent response, state and timestamps.

This is an assessment demo, not production-ready multi-tenant software. It has fictional data and no login or production tenancy controls. Do not put real customer data in it. The architecture document describes where authentication, tenant isolation, PostgreSQL row-level security, queueing, idempotency, monitoring, and scalable retrieval belong in a production system.

See:

- [`docs/architecture.md`](docs/architecture.md) — architecture explanation (sized for 2–3 pages)
- [`docs/architecture-diagram.svg`](docs/architecture-diagram.svg) — standalone architecture diagram
- [`docs/written-responses.docx`](docs/written-responses.docx) — Parts 3 and 4 response draft
- [`docs/demo-guide.md`](docs/demo-guide.md) — five-minute walkthrough outline
- [`docs/schema.sql`](docs/schema.sql) — demo schema reference

## Project structure

```text
main.py                      HTTP API, SQLite schema, retrieval, draft generation
static/index.html            Inbox and policy-management interface
static/app.css               Responsive visual system
static/app.js                Browser interactions and API calls
instance/cx_assistant.sqlite Local demo database (ignored by Git)
docs/                        Architecture, schema and submission materials
```

## Local notes

- `PORT` defaults to `5000`.
- `CX_DB_PATH` can point to another SQLite file.
- The service binds to `0.0.0.0` for Replit's preview and hosting proxy.
- The public submission URL is created by publishing the app from Replit; a running preview is not a public production URL.
- To submit the repository, connect or create a GitHub repository from Replit and push the project files. Do not commit the database or any secret.

## Known limitations

- No authentication or real tenant boundary is implemented in this demo; the two brand workspaces are sample data in one database.
- SQLite and lexical retrieval are deliberately small-scale choices. They are not the production architecture proposed in Part 2.
- A configured LLM can still produce unsupported language. The agent review step, prompt constraints, visible context and audit trail are required parts of the workflow, not optional polish.
