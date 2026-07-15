# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**Nucleus** is an AI Knowledge Assistant (RAG-based document Q&A app), early in implementation.
`spec.md` is the authoritative, condensed Single Source of Truth engineering specification — read it in
full before implementing any feature; it covers every binding rule, field list, default value, and
diagram, and takes precedence over the summary below if the two ever disagree.

Copy `.env.example` to `.env` and fill in `DATABASE_URL` (real Postgres, `postgresql+asyncpg://...`)
before running the app.

### Commands

- Run dev server: `python run.py` (uvicorn with reload, `127.0.0.1:8000`) or
  `uvicorn src.main:app --reload`
- Dependencies are pinned in `requirements.txt` (`pip install -r requirements.txt`)
- No migrations (Alembic), linter, or test suite are wired up yet — add commands here once they exist;
  do not invent them before they're real.

## Project Structure (spec.md §57–58)

```
src/
  main.py        # FastAPI app + lifespan (calls init_db/dispose on startup/shutdown)
  core/          # cross-cutting infrastructure shared by all apps — config, db, (later: security, middleware, templating)
    config/settings.py   # pydantic-settings Settings singleton, loaded from .env
    db/main.py            # async engine/session factory, get_session() FastAPI dependency
  apps/          # one package per feature/module (see spec.md §5 Modules) — auth, dashboard,
                 # assistants, documents, knowledge, chat, realtime, settings. Each app is
                 # self-contained (routes/services/repositories/models/schemas) and still follows
                 # Route → Service → Repository (§16) internally.
```

- `src/core/` holds only shared infrastructure — never business logic or feature-specific code.
- Config: import `settings` from `src.core.config.settings` — never read `os.environ` directly.
- DB: obtain sessions only via the `get_session()` dependency (`src/core/db/main.py`) — never
  instantiate `AsyncSession`/`SessionLocal` directly in route/service code.

## Project Purpose

This is a learning-focused, portfolio-quality project — explicitly **not** a commercial SaaS product.
Every feature must teach a real backend/AI engineering concept; features without educational value
should not exist. It teaches: modern FastAPI, async Python, SQLAlchemy 2.x async, RAG architecture,
pgvector, Celery background processing, and real-time (WebSocket) systems.

Core product idea: a user creates AI "assistants," each with its own uploaded documents. Documents are
processed into embeddings in the background and become retrievable; chat with an assistant is
Retrieval-Augmented Generation (retrieve relevant chunks, then generate an answer), streamed to the
browser like ChatGPT.

## Technology Stack

- **Backend**: FastAPI, SQLAlchemy 2.x (async), Alembic, PostgreSQL (hosted on Neon)
- **Infra**: Redis (Celery broker), Celery (background jobs — document processing), pgvector (vector
  search lives *inside* Postgres — no separate vector DB)
- **Frontend**: Jinja2 (server-rendered HTML), HTMX (dynamic updates), Alpine.js (small client
  interactions only), Tailwind CSS. Explicitly **no SPA framework**.
- **AI**: LangChain used only as a toolkit (document loaders, text splitters, embedding/chat model
  wrappers) — never as the application's architecture. OpenAI-compatible APIs for LLM and embeddings,
  but every AI component (LLM, embedding provider, vector store) must be swappable with minimal changes.
- **Real-time**: native FastAPI WebSockets for streaming LLM tokens and processing progress.
- **Auth**: server-side sessions with an opaque cookie (`session_id`) — explicitly **not** JWT.

## Non-Negotiable Architectural Rules (spec.md §16)

Strict one-way dependency flow — never reversed:

```
Route Handler → Service → Repository → Database
```

- Route handlers coordinate only; they must never contain business logic.
- Services perform business logic (validation, orchestration, ownership checks). Services never depend
  on route handlers or templates.
- Repositories do persistence only (insert/update/delete/query) — no business logic, and repositories
  never call services.
- Jinja templates render prepared data only — no DB queries, no business logic, no AI calls in templates.

## Domain Model (spec.md §9, lifecycles §12–13)

```
User ──1:N── Assistant ──1:N── Document ──1:N── DocumentChunk ── Embedding (pgvector column)
User ──1:N── Conversation (belongs to an Assistant) ──1:N── Message (role: user | assistant)
```

- Every resource has exactly one owner; no sharing, orgs, or workspaces. Authorization is pure
  ownership-based and enforced in the service layer (not templates/routes).
- All primary keys are UUIDs. Foreign keys are always enforced at the DB level.
- No soft deletes in v1 — deletion is permanent.
- The embedding vector is stored directly on `DocumentChunk` via a pgvector column; there is no
  external/dedicated vector database.
- Document processing states: `UPLOADED → QUEUED → PROCESSING → COMPLETED | FAILED` (stored as a DB enum).

## Service Layer (spec.md §14–15)

Expected services: `AuthenticationService`, `AssistantService`, `DocumentService`, `KnowledgeService`
(extraction/chunking/embedding/indexing), `ConversationService`, `ChatService` (retrieval + prompt
construction + LLM invocation + streaming), `EmbeddingService`, `RetrieverService`, `LLMService`.

Expected repositories (persistence only): `UserRepository`, `AssistantRepository`,
`DocumentRepository`, `ConversationRepository`, `MessageRepository`.

## RAG Pipeline (spec.md §17–33)

Ingestion (async, via Celery, triggered on document upload):
```
Upload → Store Original File → Queue Celery Job → Extract Text → Clean Text →
Split Into Chunks (recursive character splitter, default size 1000 / overlap 200,
configurable per assistant) → Generate Embeddings → Store in pgvector → Ready
```

Chat / retrieval (every user message):
```
User Question → Embedding → Cosine Similarity Search (pgvector) → Top-K chunks
(default K=5, configurable per assistant) → Prompt Construction → LLM → Streamed Response
```

Key rules:
- Retrieval always precedes generation; the app must attempt retrieval before falling back to the LLM's
  own knowledge.
- The LLM is stateless — conversation history and retrieved context are supplied by the app on every
  call; never treat the LLM as memory.
- The **same embedding model** must be used for indexing and querying; changing one without the other
  invalidates search quality.
- Prompt assembly (system prompt + retrieved context + conversation history + user question) is done by
  application code, not delegated to LangChain, and instructions/retrieved content must stay clearly
  separated in the prompt.
- The original uploaded file is never deleted after embedding generation (needed for future
  reprocessing); DB stores metadata, filesystem stores the file itself.

## Auth Model (spec.md §35–44)

- Server-side sessions only, no JWT. Browser cookie holds only an opaque `session_id`
  (`HttpOnly`, `Secure`, `SameSite=Lax` in production) — never email/user id/permissions/JSON.
- Session store is an abstraction: in-memory for dev, Redis in production.
- Passwords hashed with Argon2id, with transparent rehashing on parameter upgrades.
- Changing password invalidates all other sessions except the current one.
- No roles/permissions/orgs — authorization is "do you own this resource," checked in services.
- v1 excludes: OAuth, MFA, password reset, email verification, magic links, API keys.

## Explicit Non-Goals (spec.md §8, deferred AI features §34)

Do not build unless the spec is revised: OAuth/MFA/password reset/email verification, AI agents/tool
calling/MCP/function calling/multi-agent systems/long-term memory, hybrid search, re-ranking,
query expansion, graph RAG, billing/teams/orgs/multi-tenancy/admin dashboard, Kubernetes/microservices/
event sourcing/CQRS. These are intentionally deferred to keep the learning scope focused.

## Frontend Conventions (spec.md §45–56)

- Prefer returning HTML over JSON; HTMX requests get partial-template fragments, not JSON APIs.
- Alpine.js is for pure UI state (dropdowns, modals, tabs) — never duplicate server-side state in Alpine.
- Templates are organized as `layouts/`, `pages/`, `partials/` (HTMX fragments), `components/`, `macros/`.
- Forms must work without JavaScript; HTMX/Alpine enhance but are never required for correctness.
- Tailwind is the only styling approach — no Bootstrap or component libraries.
