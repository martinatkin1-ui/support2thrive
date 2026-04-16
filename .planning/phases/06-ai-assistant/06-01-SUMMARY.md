---
phase: 06-ai-assistant
plan: "01"
subsystem: assistant
tags: [rag, pgvector, lightrag, raganything, gemini, sentence-transformers, django-models, celery, crisis-detection, rate-limiting]
dependency_graph:
  requires: []
  provides:
    - apps/assistant/models.py (AssistantQuery, OrgDocument, Conversation, ConversationMessage)
    - apps/assistant/migrations/0001_initial.py (VectorExtension + all models)
    - apps/assistant/rag_service.py (get_rag_instance, build_org_content_list, build_pathway_content_list)
    - apps/assistant/crisis.py (detect_crisis, build_crisis_prefix)
    - apps/assistant/rate_limit.py (check_rate_limit)
    - apps/assistant/urls.py + views.py (stub assistant page at /assistant/)
    - apps/assistant/tests/ (32 Wave 0 tests)
  affects:
    - docker-compose.yml (pgvector image)
    - requirements.txt (raganything, pymupdf4llm added; PyPDF2 removed)
    - config/settings/base.py (LIGHTRAG_WORKING_DIR, ASSISTANT_RATE_LIMIT_*)
    - config/settings/test.py (SKIP_RAG_TESTS=True)
    - config/urls.py (assistant/ URL wired)
    - .env.example (POSTGRES_* vars, AI assistant vars)
tech_stack:
  added:
    - raganything==1.2.10 (install with --no-deps — mineru incompatible with Python 3.14)
    - pymupdf4llm==1.27.2.2 (PDF text extraction — replaces PyPDF2)
  patterns:
    - EmbeddingFunc as dataclass instantiation (lightrag 1.4.14 actual API — not decorator)
    - asyncio.Lock() for singleton pattern in async context
    - session-based rate limiting (no DB required)
    - substring matching for crisis keyword detection
key_files:
  created:
    - apps/assistant/models.py
    - apps/assistant/forms.py
    - apps/assistant/migrations/0001_initial.py
    - apps/assistant/migrations/__init__.py
    - apps/assistant/rag_service.py
    - apps/assistant/crisis.py
    - apps/assistant/rate_limit.py
    - apps/assistant/views.py (stub)
    - apps/assistant/urls.py (stub)
    - apps/assistant/tests/__init__.py
    - apps/assistant/tests/test_models.py
    - apps/assistant/tests/test_crisis.py
    - apps/assistant/tests/test_rate_limit.py
    - apps/assistant/tests/test_views.py
    - apps/assistant/tests/test_tasks.py
    - templates/assistant/chat.html (stub)
  modified:
    - docker-compose.yml
    - requirements.txt
    - config/settings/base.py
    - config/settings/test.py
    - config/urls.py
    - .env.example
decisions:
  - "EmbeddingFunc in lightrag 1.4.14 is a dataclass, not a decorator — instantiated directly with func= argument"
  - "crisis.py and rate_limit.py created in Plan 06-01 (not 06-03 as plan assumed) — required for Wave 0 tests to pass"
  - "Stub views.py/urls.py/chat.html added to wire /assistant/ URL so test_views.py passes — replaced in Plan 06-03"
  - "all-MiniLM-L6-v2 (384-dim) chosen for embeddings — faster, sufficient for community services queries"
  - "hurting myself added to self_harm keywords (test-driven: test_self_harm_keyword_hurt_myself required it)"
metrics:
  duration: "~13 minutes"
  completed: "2026-04-16T08:00:22Z"
  tasks_completed: 3
  tasks_total: 3
  files_created: 16
  files_modified: 6
---

# Phase 6 Plan 01: Infrastructure, Models, RAG Service, Wave 0 Tests — Summary

**One-liner:** pgvector Docker image, Django assistant models with VectorExtension migration, RAGAnything singleton using LightRAG PG backend + Gemini 2.5 Flash + sentence-transformers, crisis/rate-limit modules, and 32 Wave 0 test stubs.

---

## What Was Built

### Task 1: Infrastructure (commit 4d6868b)

- `docker-compose.yml`: Changed `postgres:16-alpine` to `pgvector/pgvector:pg16`
- `requirements.txt`: Added `raganything==1.2.10` and `pymupdf4llm==1.27.2.2`; removed `PyPDF2==3.0.1`
- `config/settings/base.py`: Added `LIGHTRAG_WORKING_DIR`, `ASSISTANT_RATE_LIMIT_SESSION`, `ASSISTANT_RATE_LIMIT_MINUTE`
- `config/settings/test.py`: Added `SKIP_RAG_TESTS = True` and `LIGHTRAG_WORKING_DIR = "/tmp/rag_storage_test"`
- `.env.example`: Added `POSTGRES_*` pgvector env vars and AI assistant vars

### Task 2: Models + Migration (commit b4e2b9d)

- `apps/assistant/models.py`: Four models — `AssistantQuery`, `Conversation`, `ConversationMessage`, `OrgDocument`
  - All strings wrapped in `gettext_lazy _()`
  - `OrgDocument`: `FileExtensionValidator(allowed_extensions=["pdf"])`, FK to Organization and User
  - `AssistantQuery`: Docstring explicitly warns against storing PII (T-6-09 mitigated)
- `apps/assistant/forms.py`: `OrgDocumentForm` with 20MB size limit in `clean_file()` (T-6-03a mitigated)
- `apps/assistant/migrations/0001_initial.py`: `VectorExtension()` as first operation — safe on SQLite (no-op), required for Postgres pgvector

### Task 3: RAG Service + Wave 0 Tests (commit 01de9ec)

- `apps/assistant/rag_service.py`:
  - `get_rag_instance()`: async singleton, thread-safe via `asyncio.Lock()`
  - `embedding_func`: `EmbeddingFunc` dataclass wrapping `all-MiniLM-L6-v2` (384-dim)
  - `build_org_content_list(org_id)`: Builds `insert_content_list` payload from Organization + services
  - `build_pathway_content_list(pathway_id)`: Builds payload from Pathway + sections + guide items
  - `gemini-2.5-flash` LLM via `partial(gemini_model_complete, model_name="gemini-2.5-flash")`
  - LightRAG PG storage: `PGKVStorage`, `PGVectorStorage`, `PGGraphStorage`, `PGDocStatusStorage`
- `apps/assistant/crisis.py`: `detect_crisis()` + `build_crisis_prefix()`, 5 keyword categories, 30+ keywords
- `apps/assistant/rate_limit.py`: `check_rate_limit()` — session budget + per-minute rolling window
- Stub `views.py`, `urls.py`, `templates/assistant/chat.html` to enable URL test to pass
- 6 test modules: 32 tests, all passing

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] EmbeddingFunc is a dataclass, not a decorator**
- **Found during:** Task 3 — `TypeError: EmbeddingFunc.__init__() missing 1 required positional argument: 'func'`
- **Issue:** Research doc (and plan) showed `@EmbeddingFunc(embedding_dim=384, max_token_size=512)` decorator pattern. In lightrag 1.4.14, `EmbeddingFunc` is a `@dataclass` requiring `func` as a mandatory positional argument.
- **Fix:** Defined `async def _embedding_func_impl(texts)` then instantiated `embedding_func = EmbeddingFunc(embedding_dim=384, max_token_size=512, func=_embedding_func_impl)`
- **Files modified:** `apps/assistant/rag_service.py`
- **Commit:** 01de9ec

**2. [Rule 2 - Missing functionality] crisis.py and rate_limit.py created in Plan 06-01**
- **Found during:** Task 3 — Wave 0 tests import `apps.assistant.crisis` and `apps.assistant.rate_limit` at test time. These were intended for Plan 06-03 but tests fail without them.
- **Fix:** Created both modules in Plan 06-01. Content matches exactly what the research doc specified.
- **Files modified:** `apps/assistant/crisis.py`, `apps/assistant/rate_limit.py` (new)
- **Commit:** 01de9ec

**3. [Rule 1 - Bug] Crisis keyword "hurting myself" missing from keyword list**
- **Found during:** Task 3 — `test_self_harm_keyword_hurt_myself` tested `"I feel like hurting myself"` which doesn't match `"hurt myself"` (substring mismatch).
- **Fix:** Added `"hurting myself"` to the `self_harm` keyword list in `crisis.py`
- **Files modified:** `apps/assistant/crisis.py`
- **Commit:** 01de9ec

**4. [Rule 2 - Missing functionality] Stub views/URLs needed for test_views.py**
- **Found during:** Task 3 — `test_assistant_page_renders` hits `/en/assistant/` which requires a registered URL. Plan deferred views to Plan 06-03.
- **Fix:** Created stub `views.py`, `urls.py`, `templates/assistant/chat.html` and wired into `config/urls.py`. Plan 06-03 replaces with full implementation.
- **Files modified:** `apps/assistant/views.py`, `apps/assistant/urls.py`, `templates/assistant/chat.html`, `config/urls.py` (new/modified)
- **Commit:** 01de9ec

**5. [Rule 1 - Bug] PathwaySection uses `body` field, not `intro`**
- **Found during:** Task 3 — plan code snippet used `section.intro` but `apps/pathways/models.py` defines the field as `body`.
- **Fix:** Used `section.body` in `build_pathway_content_list()`.
- **Files modified:** `apps/assistant/rag_service.py`
- **Commit:** 01de9ec

---

## Out-of-Scope Pre-existing Issue (Deferred)

**Template syntax error in `templates/portal/onboarding/step_referral_config.html`:**
```
TemplateSyntaxError: Could not parse the remainder: '=="help_text"' from 'field.name=="help_text"'
```
This error existed in the working tree before Plan 06-01 started (visible in the initial git status as a modified file). It is unrelated to assistant infrastructure. The full suite runs 197 tests with 1 pre-existing error; 32 new assistant tests all pass.

---

## Test Results

| Test Module | Tests | Status |
|---|---|---|
| `test_models.py` | 3 | PASS |
| `test_crisis.py` | 20 | PASS |
| `test_rate_limit.py` | 5 | PASS |
| `test_views.py` | 2 | PASS |
| `test_tasks.py` | 2 | PASS |
| **Total** | **32** | **PASS** |

Full suite: 197 tests (32 new + 165 prior), 1 pre-existing failure in `step_referral_config.html` (out of scope).

---

## Known Stubs

| File | Stub | Reason |
|---|---|---|
| `templates/assistant/chat.html` | No chat UI | Full interface in Plan 06-03 |
| `apps/assistant/views.py` | `assistant_page` returns static render | Full streaming chat view in Plan 06-03 |
| `apps/assistant/tests/test_views.py` | `test_session_history_capped` has no real assertion | Full assertion needs stream view (Plan 06-03) |
| `apps/assistant/tests/test_tasks.py` | `test_content_list_has_required_keys` only checks callable | Full Celery task test in Plan 06-02 |
| `apps/assistant/tests/test_crisis.py` | All crisis tests | crisis.py IS implemented — tests are fully functional |
| `apps/assistant/tests/test_rate_limit.py` | All rate limit tests | rate_limit.py IS implemented — tests are fully functional |

---

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what was planned.

Mitigations applied per threat register:
- T-6-09: `AssistantQuery` docstring explicitly prohibits PII in `query_text`/`response_text`
- T-6-03a: `OrgDocumentForm.clean_file()` rejects > 20MB; `FileExtensionValidator` rejects non-PDF
- T-6-04/T-6-05: No credentials in `rag_service.py` logs; all Postgres/Gemini config via env vars only

---

## Self-Check: PASSED

All created files verified present. All 3 task commits found (4d6868b, b4e2b9d, 01de9ec). 32 assistant tests pass.
