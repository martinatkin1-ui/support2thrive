# Phase 6 — AI Assistant: Context & Decisions

**Captured:** 2026-04-13
**Status:** Ready for research → planning

---

## Domain Boundary

Phase 6 delivers a **RAG-powered AI chat assistant** at `/assistant/` that helps any user navigate community services. It can answer questions using knowledge extracted from orgs, services, uploaded PDFs, and pathway content.

New capabilities (notifications, newsfeed completion, search) are **out of scope** — they belong to a future phase.

---

## Decisions

### 1. Dev Vector Store
**Decision:** Docker Postgres with pgvector (update docker-compose.yml).

- `pgvector==0.4.2` and `psycopg2-binary==2.9.11` already in requirements.txt
- Dev currently uses SQLite — incompatible with pgvector
- Add `postgres:16-pgvector` service to docker-compose.yml
- Update `.env` `DATABASE_URL` to use Postgres when running via Docker
- Test settings (`config/settings/test.py`) can stay in-memory SQLite — skip vector tests in test DB or mock the embedding calls
- No SQLite fallback code path — one code path, Postgres for anything touching the assistant

### 2. RAG System — RAG-Anything (HKUDS)
**Decision:** Use [RAG-Anything](https://github.com/HKUDS/RAG-Anything) as the RAG framework.

- `pip install raganything` — library, no separate server required
- **Document parsing:** MinerU (replaces PyPDF2 — remove `PyPDF2==3.0.1` from requirements.txt; it is already unused in the codebase)
- **Retrieval:** LightRAG knowledge graph + pgvector backend — entity/relationship extraction over documents
- **LLM:** Gemini 2.5 Flash via RAG-Anything's `llm_model_func` callback (existing `GEMINI_API_KEY` setting)
- **Embeddings:** RAG-Anything's embedding pipeline (configurable; sentence-transformers available if needed)
- **Async processing:** Wrap RAG-Anything indexing operations in Celery tasks (Redis already configured)
- **Python 3.14 compatibility:** Verify before coding — LightRAG team is active, but confirm `raganything` wheel works on 3.14.3
- **MinerU optional deps:** PaddleOCR for scanned docs; LibreOffice for Office files — include in Docker image, optional on dev

### 3. Content Scope for Indexing
**Decision:** Index the following content types:

| Content | Source | Update trigger |
|---------|--------|----------------|
| Organization profiles | `apps/organizations/` | `post_save` signal → Celery task |
| Services | `apps/organizations/` + `apps/services/` | `post_save` signal → Celery task |
| Pathways + guide items | `apps/pathways/` | `post_save` signal → Celery task |
| Org-uploaded PDFs | `apps/organizations/` (new FileField) | Upload → Celery task via RAG-Anything |

**Out of scope for Phase 6:**
- Events (time-sensitive, stale data risk)
- Newsfeed (app is stubbed, not implemented)
- Obsidian vault (`OBSIDIAN_VAULT_PATH` in .env) — deferred to future phase

### 4. Chat Interaction Model
**Decision:**
- **Entry point:** Dedicated page at `/assistant/` (wired into i18n_patterns)
- **Interaction:** Multi-turn conversation with session-scoped history
- **History storage:** Django session (`request.session`) — cleared on browser close; no DB persistence for Phase 6
- **Display:** HTMX for streaming response display (consistent with existing HTMX patterns in the project)
- **Access:** Public (no login required) — consistent with `public` role being able to use the assistant per CLAUDE.md
- **Rate limiting:** Per-session message budget (configurable, e.g. 20 messages/session) to prevent abuse

### 5. Response Style & Safety
**Decision:**

**Tone:** Warm, plain English, non-jargon. Empathetic and accessible for users who may be in crisis or have literacy barriers.
- Example: "Here's a place that can help you with housing..." not "The following organisations provide accommodation services..."
- Use simple sentences, avoid acronyms unless explained

**Source citations:** Always shown in every response — org names as clickable links to their platform detail pages.

**Crisis handling:** Detect crisis keywords (self-harm, suicidal ideation, rough sleeping emergency, domestic violence emergency). On detection:
1. Immediately surface emergency contacts at the top of the response:
   - Samaritans: 116 123 (free, 24/7)
   - Crisis text line / local equivalents
   - 999 for immediate danger
2. Then continue with helpful service information — do NOT refuse
3. These users need help most; refusal is the worst outcome

**Language:** All UI strings `{% trans %}`-wrapped (10-language i18n). AI-generated response content is English-only for Phase 6 — translation of AI responses deferred.

---

## Canonical References

- `ROADMAP.md` — Phase 6 milestone breakdown (pgvector, indexing pipeline, chat UI, Gemini RAG)
- `REQUIREMENTS.md` — Platform-wide requirements (PII, audit logging, i18n)
- `RESEARCH.md` — PDF processing library comparison (pymupdf4llm vs RAG-Anything, Python 3.14 compat notes)
- `apps/assistant/` — Skeleton app (empty models, no views/urls/migrations — Phase 6 builds this out)
- `apps/referrals/encryption.py` — Fernet encryption pattern (reference for any PII in assistant logs)
- `apps/referrals/tasks.py` — Celery task patterns to follow
- `config/settings/base.py` — `GEMINI_API_KEY` already configured
- `docker-compose.yml` — Add pgvector Postgres service here
- `design-system/MASTER.md` — Figtree/Noto Sans fonts, amber CTAs, WCAG AAA — chat UI must follow this
- [RAG-Anything GitHub](https://github.com/HKUDS/RAG-Anything) — Framework docs and configuration reference

---

## Pre-Implementation Checklist

Before planning begins, researcher should verify:
- [ ] `raganything` installs on Python 3.14.3 (check PyPI wheel tags or test in venv)
- [ ] Gemini 2.5 Flash `llm_model_func` callback format for RAG-Anything / LightRAG
- [ ] MinerU Docker image size and whether PaddleOCR is required for Phase 6 scope (most org PDFs are text-heavy, not scanned)
- [ ] LightRAG pgvector backend configuration (which tables it creates, migration strategy)
- [ ] HTMX streaming pattern for Gemini response (Server-Sent Events vs. polling)

---

## Deferred Ideas (not in Phase 6)

- Obsidian vault sync (OBSIDIAN_VAULT_PATH in .env — noted for future phase)
- AI response translation (English-only for Phase 6)
- Floating widget on all pages (Phase 6 is dedicated page only)
- Events indexing (time-sensitive, deferred)
- Newsfeed indexing (app is stubbed)
- Conversation DB persistence / user history across sessions
