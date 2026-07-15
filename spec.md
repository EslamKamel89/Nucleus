# Nucleus — Spec Summary (SSOT condensed)

Condensed from `spec.md` (authoritative). Consult `spec.md` only for narrative/examples; this file has
every binding rule, field list, and diagram.

## 1. Purpose & Scope

Portfolio/learning project (not commercial SaaS) for mastering FastAPI, async Python, SQLAlchemy 2.x
async, LangChain, RAG, vector DBs, real-time systems. Every feature must teach something; no feature
exists without educational value.

**Product**: users create AI "assistants," each owning documents + conversations. Uploaded docs are
background-processed into embeddings; chat retrieves relevant chunks then generates an LLM answer
(RAG), streamed to the browser (ChatGPT-like UX). Use cases: support bots, internal docs, HR/legal
knowledge bases, course notes, API docs.

## 2. Core Principles

1. Understand every line — nothing copied blindly from tutorials.
2. Backend-first; frontend stays intentionally simple.
3. Server-rendered by default; prefer HTML over JSON; HTMX not SPA.
4. Async only where it has measurable value (DB, websockets, streaming, HTTP calls, file uploads) — not for fashion.
5. Business logic never in route handlers: **Route → Service → Repository**.
6. Everything replaceable: LLM (OpenAI→Anthropic), embeddings (OpenAI→Voyage→Nomic→BGE), vector store (pgvector→Qdrant) — app logic shouldn't need to change.
7. No interfaces/abstractions until there's a real reason; prefer clarity over flexibility.
8. Build only what teaches something valuable.

## 3. Tech Stack

- **FastAPI** — async Python web framework.
- **SQLAlchemy 2.x async** + **Alembic** — ORM + migrations.
- **PostgreSQL (Neon-hosted)** — relational DB, also vector store via **pgvector** (no separate vector DB).
- **Redis** — Celery broker (caching later).
- **Celery** — background processing (document ingestion, long AI tasks).
- **WebSockets** (native FastAPI) — streaming responses, progress updates.
- **Jinja2** — server-rendered HTML. **HTMX** — dynamic UX w/o SPA. **Alpine.js** — small client interactions only, never duplicates server state. **Tailwind CSS** — only styling method, no component libs.
- **LangChain** — used intentionally as a toolkit only (loaders, splitters, embedding/chat model wrappers, output parsers); never the app architecture.
- **LLM/Embeddings** — OpenAI-compatible API initially; provider must be swappable.

## 4. System Architecture

```
Browser --HTTP/HTMX + WebSocket--> FastAPI --> {Auth, Business Logic, AI Services} --> Async SQLAlchemy --> PostgreSQL(Neon) + pgvector
```
Ingestion: `Upload -> Celery -> Text Extraction -> Chunking -> Embeddings -> pgvector`
Chat: `Chat -> Retriever -> Relevant Chunks -> Prompt Builder -> LLM -> Streaming Response -> Browser`

## 5. Modules

1. **Authentication** — register, login, logout, profile, change password.
2. **Dashboard** — resource overview, recent activity, system status.
3. **Assistants** — CRUD; each owns prompt, documents, conversations.
4. **Documents** — upload/manage knowledge sources.
5. **Knowledge Processing** — docs → searchable vectors.
6. **Chat** — conversation UI, streaming, history.
7. **Real-Time** — progress notifications, streaming, live updates.
8. **Settings** — global AI defaults.

## 6. User Journey

Register → Login → Dashboard → Create Assistant → Upload Documents → Background Processing →
Knowledge Indexed → Start Chat → Ask Questions → Retrieve Context → LLM Response → Continue Conversation.

## 7. Functional Scope (v1)

- **Auth**: Register, Login, Logout, Profile, Change Password.
- **Dashboard**: assistant count, document count, conversation count, processing jobs.
- **Assistants**: Create/Edit/Delete/List/View. Fields: name, description, system prompt, temperature, model.
- **Documents**: types PDF/TXT/Markdown. Features: upload, delete, list, processing status, metadata.
- **Knowledge Processing** (automatic): extract text → clean → chunk → embed → store vectors.
- **Chat**: new conversation, history, streaming, semantic retrieval, markdown rendering, citations (if available).
- **Settings**: default model, chunk size, chunk overlap, retrieval count, temperature.

## 8. Explicit Non-Goals (v1)

- **Auth**: OAuth, Google/GitHub login, MFA, password reset, email verification, magic links, API keys.
- **AI**: agents, tool calling, MCP, function calling, multi-agent systems, long-term memory, autonomous agents.
- **Platform**: billing, teams, orgs, multi-tenancy, admin dashboard, analytics, subscriptions, notifications, email campaigns.
- **Infra**: Kubernetes, microservices, event sourcing, CQRS.

## 9. Domain Model

```
User --1:N--> Assistant --1:N--> Document --1:N--> DocumentChunk --1:1--> Embedding (pgvector)
User --1:N--> Conversation --1:N--> Message
Assistant --1:N--> Conversation
```
One owner per resource; no sharing/orgs/workspaces.

**User** — auth + own assistants/conversations only; never holds AI-specific data.
Fields: standard identity/auth fields (not enumerated beyond relationships).

**Assistant** — defines AI behavior (personality, model, prompt config, retrieval config); owns documents + conversations.
Fields: id, user_id, name, description, system_prompt, model_name, temperature, created_at, updated_at.

**Document** — represents an uploaded file; original file is source of truth, extracted text is derived. Never stores embeddings directly. Formats: PDF, TXT, Markdown.
Fields: id, assistant_id, filename, original_filename, mime_type, size, status, uploaded_at.

**DocumentChunk** — one semantically meaningful text piece of a document; exists because LLMs can't consume whole docs.
Fields: id, document_id, chunk_index, content, token_count, page_number (nullable), vector (pgvector — no external vector DB).

**Conversation** — one chat session, belongs to one assistant.
Fields: id, assistant_id, title, created_at, updated_at.

**Message** — one message in a conversation. Roles: `user`, `assistant` only (no system messages stored — system prompt lives on Assistant).
Fields: id, conversation_id, role, message, created_at.

## 10. Database Principles

- Relational; Postgres is SSOT. Vector DB **is** Postgres via pgvector (simplifies deploy/backup/migration/local dev).
- Normalize where appropriate; avoid premature denormalization.
- Primary keys: UUID everywhere (safer URLs, scaling, no sequential exposure, easier merging).
- Foreign keys always enforced at DB level, never app-only.
- Every major entity: `created_at`, `updated_at` (DB-generated where practical).
- **No soft deletes in v1** — deletion is permanent (simpler queries/learning, fewer edge cases).

## 11. File Storage

- DB stores metadata: filename, path, mime type, size.
- Filesystem stores the actual file.
- Never delete the original file after embedding generation — needed for future reprocessing.

## 12. Document Processing Lifecycle

`UPLOADED → QUEUED → PROCESSING → COMPLETED` (or `→ FAILED` on error); stored as a DB enum. Failed docs may be reprocessed.
Detailed pipeline: Uploaded → Queued → Extracting Text → Chunking → Generating Embeddings → Saving Vectors → Completed.

## 13. Assistant / Conversation Lifecycles

Assistant: Create → Configure Prompt → Upload Documents → Knowledge Processing → Ready → Chat.
An assistant with zero documents is valid and answers using only its system prompt.

Conversation: Create → User Message → Retrieve Context → Generate Response → Assistant Message → repeat.
Conversations are immutable except title; messages are never edited after creation.

## 14. Application Services (business logic layer, never in routes)

- **AuthenticationService** — register, login, logout, password change.
- **AssistantService** — CRUD, configuration, validation.
- **DocumentService** — upload, delete, metadata, retrieval.
- **KnowledgeService** — extraction, chunking, embedding generation, indexing.
- **ConversationService** — create conversations, store messages, history retrieval.
- **ChatService** — retrieval, prompt construction, LLM invocation, streaming.
- **EmbeddingService** — generate embeddings, talk to embedding provider.
- **RetrieverService** — semantic search, ranking, top-k retrieval.
- **LLMService** — talk to LLM provider, stream responses, hide provider details.

## 15. Repository Layer (persistence only, no business logic)

`UserRepository`, `AssistantRepository`, `DocumentRepository`, `ConversationRepository`, `MessageRepository`.
Responsibilities: insert, update, delete, query — nothing more.

## 16. Dependency Flow (core rule, never reversed)

`Browser → Route → Service → Repository → Database`
Repositories never call services; services never depend on route handlers; business rules never in templates.

## 17. AI Architecture & Design Principles

Goal: understand production RAG engineering, not just call an LLM.

1. Always attempt retrieval first; LLM must not answer from pretrained knowledge alone when user knowledge exists.
2. LLM is stateless — app supplies history + context every call; never treat LLM as storage.
3. LangChain is orchestration only (loaders, splitters, embedding providers, chat models, output parsers), not the architecture; business logic lives in services.
4. App owns the full retrieval pipeline end-to-end; avoid black-box abstractions.
5. Every AI operation (LLM, embedding model, vector search) must be replaceable with minimal code change.

## 18. RAG Pipeline

`User Question → Conversation History → Embedding Generation → Vector Search → Relevant Chunks → Prompt Construction → LLM → Streaming Response`
Every stage independently testable.

## 19. Knowledge Ingestion Pipeline

`Upload File → Store Original → Queue Celery Job → Extract Text → Clean Text → Split Into Chunks → Generate Embeddings → Store in pgvector → Knowledge Ready`
Each stage should log clearly and emit progress updates.

## 20. Document Loading

v1 formats: PDF, Plain Text, Markdown. Loader extracts raw text only — no splitting, no embedding, no LLM calls (later stages' job).

## 21. Text Cleaning

Before chunking: normalize whitespace, remove repeated blank lines, trim, preserve paragraph boundaries. Goal: improve chunk quality without altering meaning.

## 22. Chunking Strategy

Recursive character-based splitting via LangChain (simplicity + effectiveness balance). Poor chunking → poor retrieval.
- Configurable per assistant: chunk size (default **1000** chars), chunk overlap (default **200** chars).
- A good chunk: one coherent idea, preserves context, small enough for retrieval, avoids splitting sentences.

## 23. Embeddings

- Same embedding model **must** be used for indexing and querying (mandatory) — mismatch invalidates search.
- Provider: OpenAI-compatible embedding API initially; architecture must allow swapping later.

## 24. Vector Database

PostgreSQL + pgvector (Neon-hosted); no dedicated vector DB (simpler infra, single SSOT, easier backup/migration, deeper pgvector learning).
Each chunk stores: text, metadata, embedding vector (pgvector column type).
Metadata per chunk: document id, document filename, chunk index, page number (if available) — extensible later without architecture change.

## 25. Retrieval Strategy

`User Question → Generate Embedding → Vector Similarity Search (cosine, via pgvector, indexed) → Top-K Results → Build Context → Prompt → LLM`
Retrieval always precedes generation. Top-K is configurable per assistant, default **5**.

## 26. Prompt Construction

App (not LangChain) assembles: system prompt + retrieved context + conversation history + current user message → single prompt. Must stay deterministic and easy to inspect.

## 27. Assistant System Prompt

Owned per-assistant; defines identity/behavior, independent of retrieved knowledge (e.g. "customer support assistant", "senior Python instructor", "legal assistant answering only from supplied docs").

## 28. Context Injection

Keep clearly separated in the prompt: System Prompt / Knowledge Context / Conversation History / User Question. Never mix instructions with retrieved content.

## 29. Conversation Memory

Short-term only = prior messages in current conversation, fetched by the app. No long-term memory system. LLM remains stateless.

## 30. Streaming Responses

Stream token-by-token when provider supports it (better UX, lower perceived latency, showcases async, pairs with WebSockets).
`LLM → Token Stream → WebSocket → Browser → Live UI Updates`

## 31. Citations

Include references to source document(s) when possible; basic references suffice for v1; architecture should allow richer citations later.

## 32. AI Configuration (per assistant)

model, system prompt, temperature, chunk size, chunk overlap, top-k retrieval — scoped to that assistant only.

## 33. Error Handling (AI ops)

Handle gracefully: LLM unavailable, embedding API unavailable, vector search error, malformed document, unsupported file, timeout, rate limiting. Never expose internal details to users; log meaningfully for devs.

## 34. Future AI Features (deferred, not v1)

Hybrid search, query expansion, re-ranking, parent/child retrieval, multi-vector retrieval, context compression, self-query retrieval, Graph RAG, knowledge graphs, agentic workflows, tool/function calling, MCP, long-term memory, reflection loops, multi-agent systems, automatic prompt optimization, retrieval evaluation frameworks. v1 architecture should allow adding these later without redesign.

## 35. Authentication Architecture

Authentication = identify user; authorization = what they can access. v1 authorization is deliberately simple: every user owns their resources; no roles/permissions/orgs.

Principles:
1. Server-side sessions, **not JWT** (better Jinja/HTMX fit, simpler mental model, no refresh tokens, no client-side auth logic).
2. Browser stores only an opaque session id; everything else server-side.
3. Feel Django-like: routes just ask for "current user"; auth details hidden.

## 36. Authentication Features

v1: Register, Login, Logout, Profile, Change Password.
Excluded: email verification, password reset, OAuth, MFA, magic links, API keys.

Flow: `Register → Login → Authenticated Session → Protected Pages → Logout`

## 37. Registration

Fields: Name, Email, Password, Confirm Password. Validation: unique email, valid email, password policy. Successful registration allows immediate login (no email verification).

## 38. Login

Credentials: email, password. Success → Create Session → Store Session → Set Secure Cookie → Redirect Dashboard. Failure → return validation error.

## 39. Session Architecture

Browser stores `session_id` only. Server stores `session_id → user_id, expiration, last_activity`.
Storage: dev = memory, prod = Redis, behind a `SessionStore` abstraction.
Cookie settings (prod): `HttpOnly=true`, `Secure=true`, `SameSite=Lax`, `Path=/`. Cookie must never contain email/user id/permissions/JSON/JWT — session id only.

## 40. Profile

Editable: name. Future: avatar, timezone, language. No email changes in v1.

## 41. Change Password

Requires: current password, new password, confirmation. Success invalidates all other sessions except current one.

## 42. Password Storage

Hashed (never encrypted) with **Argon2id**. App should transparently upgrade hashes when algorithm parameters change.

## 43. Route Protection

Protected (require auth, redirect anonymous to Login): Dashboard, Assistants, Documents, Chat, Profile.
Public: Login, Register.

## 44. Authorization

Ownership-based only: User A may access Assistant A but not Assistant B. Ownership checks live in services — never templates or route handlers.

## 45. Frontend Architecture

Server-rendered: FastAPI returns HTML; HTMX progressively enhances; Alpine adds lightweight interactions. No frontend state management library.

## 46. Rendering Strategy

Prefer HTML; JSON only when HTML isn't practical. Browser receives ready-to-render fragments.
Page render: `Browser -> GET -> FastAPI -> Jinja -> HTML -> Browser`
HTMX render: `Browser -> HTMX Request -> FastAPI -> Partial Template -> DOM Update` (HTMX responses return only the needed fragment).

## 47. HTMX Usage

Powers: CRUD, inline editing, pagination, search, delete confirmation, status refresh, form submission. Does **not** replace WebSockets for real-time streaming.

## 48. Alpine.js Usage

Only for UI interactions: dropdown, modal, tabs, clipboard copy, keyboard shortcuts, collapsible panels. Never duplicate server-side state.

## 49. Tailwind CSS

Only CSS framework; no Bootstrap/component libraries; prefer utility classes. Custom CSS only for: global layout, typography, markdown rendering, syntax highlighting.

## 50. Jinja Guidelines

Templates = presentation only. Never query DB, run business logic, or call AI services from templates; they receive prepared data.

## 51. Template Organization

```
templates/
  layouts/     # app skeleton
  pages/       # complete pages
  partials/    # HTMX fragments
  components/  # reusable UI
  macros/      # repeated template logic
```

## 52. Navigation

Primary nav: Dashboard, Assistants, Documents, Conversations, Settings, Profile. Auth pages sit outside the main layout.

## 53. UX Principles

Feel responsive; avoid unneeded full page reloads (prefer HTMX updates). Long operations must show progress (e.g. "Uploading... 42%", "Extracting Text...", "Generating Embeddings...", "Generating response..."). User should never think the app is frozen.

## 54. Error Pages

Dedicated pages for 401, 403, 404, 500 — using normal app layout where possible.

## 55. Form Design

Every form: server-side validation, inline validation messages, CSRF protection, loading state, disabled submit while processing. Forms must work fully without JS; HTMX enhances but isn't required for correctness.

## 56. Accessibility Goals

Not the primary objective but expected: semantic HTML, proper form labels, keyboard navigation, visible focus states, sufficient color contrast, ARIA where appropriate.
