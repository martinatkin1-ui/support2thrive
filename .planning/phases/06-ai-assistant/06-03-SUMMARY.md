---
phase: 06-ai-assistant
plan: "03"
subsystem: assistant
tags: [chat-ui, sse-streaming, crisis-detection, rate-limiting, htmx, tailwind, i18n, views, templates, nav]
dependency_graph:
  requires:
    - apps/assistant/crisis.py (detect_crisis, build_crisis_prefix — from Plan 06-01)
    - apps/assistant/rate_limit.py (check_rate_limit — from Plan 06-01)
    - apps/assistant/models.py (AssistantQuery, Conversation, ConversationMessage — from Plan 06-01)
    - apps/assistant/rag_service.py (get_rag_instance — from Plan 06-01)
    - config/urls.py (assistant/ URL already wired in Plan 06-01)
  provides:
    - apps/assistant/views.py (assistant_page, chat_view, assistant_stream — full implementation)
    - apps/assistant/urls.py (page/chat/stream URL patterns)
    - templates/assistant/chat.html (full HTMX SSE chat UI with design system)
    - templates/base.html (AI Assistant nav link desktop + mobile)
    - apps/assistant/tests/test_views.py (11 tests — fully implemented)
  affects:
    - templates/base.html (nav link added)
tech_stack:
  added: []
  patterns:
    - asyncio.new_event_loop() bridge to run async LightRAG inside sync Django view (WSGI-safe)
    - StreamingHttpResponse with content_type=text/event-stream + X-Accel-Buffering: no
    - HTMX hx-ext="sse" with sse-connect/sse-swap/sse-close attributes
    - html.escape() on user content before embedding in HTML response
    - deferred import of get_rag_instance inside function body (avoids loading RAG at startup)
    - session-based pending_assistant_message handoff between chat_view and assistant_stream
key_files:
  created:
    - (none — all files existed as stubs from Plan 06-01)
  modified:
    - apps/assistant/views.py (full implementation replacing stub)
    - apps/assistant/urls.py (page/chat/stream patterns replacing stub)
    - apps/assistant/tests/test_views.py (11 tests replacing 2-test stub)
    - templates/assistant/chat.html (full chat UI replacing stub)
    - templates/base.html (AI Assistant nav link added desktop + mobile)
decisions:
  - "asyncio.new_event_loop() used in assistant_stream — WSGI sync Django cannot await directly; bridges async LightRAG into sync StreamingHttpResponse generator"
  - "get_rag_instance imported inside function body (deferred) — avoids loading sentence-transformers model at Django startup, consistent with test isolation strategy from Plan 06-02"
  - "patch target for stream test is apps.assistant.rag_service.get_rag_instance (source module) — deferred import means views module has no top-level reference to patch"
  - "html.escape() applied to user_message before embedding in HTMX response — XSS prevention (T-6-01)"
  - "Rate limit check returns HTTP 200 with error HTML (not 429) — HTMX requires 200 for hx-swap to fire"
  - "chat_view does not import get_rag_instance at all — stream endpoint only — chat_view just stores to session"
metrics:
  duration: "~20 minutes"
  completed: "2026-04-16T10:30:00Z"
  tasks_completed: 1
  tasks_total: 2
  files_created: 0
  files_modified: 5
---

# Phase 6 Plan 03: Chat Interface, SSE Streaming, Crisis Detection, Rate Limiting — Summary

**One-liner:** Full HTMX SSE chat UI at /assistant/ with asyncio-bridged LightRAG streaming, session-based rate limiting, crisis keyword detection prepending Samaritans/999 contacts, and AI Assistant nav link in desktop+mobile navigation.

---

## What Was Built

### Task 1: Chat views, URL routing, templates, nav link (commit 2d79518)

**apps/assistant/views.py** — three production views:

| View | Method | Behaviour |
|------|---------|-----------|
| `assistant_page` | GET | Renders `assistant/chat.html` with session `chat_history` |
| `chat_view` | POST | Rate-limits → saves to session + DB → returns user bubble HTML + SSE trigger div |
| `assistant_stream` | GET | SSE endpoint: crisis prefix first → async LightRAG chunks → `event: done` sentinel |

Key implementation details:
- Input truncated to 500 chars, `html.escape()` applied before embedding in response (T-6-01)
- `check_rate_limit()` called first in `chat_view` — session budget (20) + per-minute throttle (5)
- Rate limit denial returns HTTP 200 amber banner (HTMX-safe; 429 would suppress swap)
- `assistant_stream` bridges async LightRAG via `asyncio.new_event_loop()` + `loop.run_until_complete()`
- Crisis prefix (Samaritans 116 123, 999, SHOUT 85258) streamed before RAG response when keywords match
- Session `chat_history` capped at 20 items via `_cap_history()` (removes oldest pair first)
- DB writes in `try/except` — failures logged but never crash the response (non-fatal pattern)
- `get_rag_instance` imported inside function body — avoids loading sentence-transformers at startup

**apps/assistant/urls.py** — three named URL patterns:

```
/assistant/          → assistant_page  (name="page")
/assistant/chat/     → chat_view       (name="chat")
/assistant/stream/   → assistant_stream (name="stream")
```

**templates/assistant/chat.html** — full chat interface:
- Extends `base.html`, loads HTMX SSE extension in `{% block extra_head %}` only
- Design system: Figtree headings, Noto Sans body, `bg-[#FAFAF8]` page, blue-800 user bubbles, amber-500 CTA
- `#chat-messages` div with `role="log" aria-live="polite"` renders history bubbles
- `#response-area` is SSE target (populated by stream chunks)
- Form: `hx-post`, `hx-target="#chat-messages"`, `hx-swap="beforeend"`, resets input on success
- WCAG: `<label for="chat-input">` with `sr-only` class, `min-h-[44px]` touch targets, ARIA labels
- 17 `{% trans %}` strings — fully i18n-ready for all 10 languages
- Crisis notice: "If you're in immediate danger, call 999. Samaritans: 116 123."
- AI disclaimer: "AI may make mistakes — verify with organisations directly."

**templates/base.html** — nav link added:
- Desktop nav: "AI Assistant" link using `{% url 'assistant:page' %}` matching existing nav classes
- Mobile menu: same link with `min-h-[44px]` touch target

**apps/assistant/tests/test_views.py** — 11 tests:

| Class | Tests | Covers |
|-------|-------|--------|
| `AssistantPageTest` | 2 | GET returns 200, contains `<form>` |
| `ChatViewRateLimitTest` | 3 | 21st message blocked, empty ignored, valid stores to session |
| `SessionHistoryCapTest` | 3 | Cap at 20, oldest removed, session cap utility |
| `CrisisResponseInStreamTest` | 1 | Crisis keyword → `crisis_detected=True` in DB |
| `AssistantStreamTest` | 2 | Content-Type: text/event-stream, empty session → done event |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `{% trans %}` template syntax inside Python f-string**
- **Found during:** Task 1 — plan action code contained `'{% trans "Please enter a message." %}'` inside a Python f-string. Django template tags are not valid Python strings.
- **Fix:** Replaced with plain English string in the Python return value. Template strings in views.py are HTML fragments, not Django template-rendered output.
- **Files modified:** `apps/assistant/views.py`
- **Commit:** 2d79518

**2. [Rule 2 - Missing functionality] XSS protection on user content in HTML response**
- **Found during:** Task 1 — `chat_view` embeds `user_message` directly in the returned HTML f-string. Without escaping, a user could inject `<script>` tags.
- **Fix:** Added `import html` and applied `html.escape(user_message)` and `html.escape(error_msg)` before embedding in response HTML (mitigates T-6-01).
- **Files modified:** `apps/assistant/views.py`
- **Commit:** 2d79518

**3. [Rule 1 - Bug] Patch path mismatch for `get_rag_instance` in stream tests**
- **Found during:** Task 1 — Plan's test code patches `apps.assistant.views.get_rag_instance` but the import is deferred (inside the function body), so the module has no top-level attribute to patch.
- **Fix:** Used `apps.assistant.rag_service.get_rag_instance` as patch target for the stream test. Removed `get_rag_instance` patches from `chat_view` tests entirely (chat_view doesn't import it).
- **Files modified:** `apps/assistant/tests/test_views.py`
- **Commit:** 2d79518

---

## SSE Streaming Approach

The asyncio bridge pattern used in `assistant_stream`:

```python
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    response_iter = loop.run_until_complete(_get_stream())  # initialise async RAG + query
    while True:
        chunk, done = loop.run_until_complete(_next_chunk(response_iter))
        if done: break
        yield f"data: {safe_chunk}\n\n"
finally:
    loop.close()
yield "event: done\ndata: \n\n"
```

**Production deployment note (from RESEARCH.md A3):** gunicorn WSGI buffers SSE responses. For live streaming in production, use one of:
- `gunicorn --worker-class=gthread` (thread-based worker, no buffering)
- `uvicorn` ASGI worker via `gunicorn -k uvicorn.workers.UvicornWorker`

The `X-Accel-Buffering: no` header instructs nginx not to buffer the SSE stream at the reverse proxy layer.

---

## Crisis Keyword System

Keyword categories (from Plan 06-01 crisis.py — unchanged in this plan):

| Category | Example keywords |
|----------|-----------------|
| `suicidal` | kill myself, end my life, suicide, want to die |
| `self_harm` | hurt myself, hurting myself, cutting myself |
| `rough_sleeping_emergency` | nowhere to sleep tonight, sleeping rough |
| `domestic_violence` | domestic violence, unsafe at home, being abused |
| `immediate_danger` | in danger now, being attacked |

**Emergency contacts prepended on detection:**
- 999 (immediate danger)
- Samaritans: 116 123 (free, 24/7)
- Crisis text: SHOUT to 85258
- BVSC Wellbeing: 0800 111 4187

**VERIFY BEFORE DEPLOY:** WM emergency housing numbers (Wolverhampton Housing Advice 01902 556789, Birmingham City Council 0121 303 7410) are assumed — user must confirm before production launch.

---

## Rate Limit Thresholds

| Limit | Value | Setting |
|-------|-------|---------|
| Session budget | 20 messages | `ASSISTANT_RATE_LIMIT_SESSION` |
| Per-minute throttle | 5 messages/60s | `ASSISTANT_RATE_LIMIT_MINUTE` |

Both configurable via environment variables. Enforced server-side in `request.session`.

---

## Test Results

| Test Module | Tests | Status |
|---|---|---|
| `test_crisis.py` | 20 | PASS |
| `test_rate_limit.py` | 5 | PASS |
| `test_views.py` | 11 | PASS |
| `test_models.py` | 3 | PASS |
| `test_tasks.py` | 7 | PASS |
| **Assistant total** | **46** | **PASS** |

Full suite: 176 tests pass (46 assistant + 130 prior phases).

---

## Known Stubs

None — all planned stubs from Plans 06-01 and 06-02 are now replaced with full implementations.

The `{% block extra_head %}` SSE script tag in `chat.html` is intentional — the HTMX SSE extension is loaded only on the assistant page, not globally.

---

## Threat Surface Scan

Two new network endpoints introduced:
- `POST /en/assistant/chat/` — user-submitted message
- `GET /en/assistant/stream/` — SSE response stream

Both were in the plan's threat model (T-6-01, T-6-02, T-6-06, T-6-04, T-6-07, T-6-08, T-6-09). No new surface beyond what was planned.

Mitigations applied:
- T-6-01 (Tampering): `html.escape()` on user content, 500-char truncation
- T-6-02 (DoS): `check_rate_limit()` enforced before any Gemini API call
- T-6-04 (Info disclosure): `GEMINI_API_KEY` never logged or returned
- T-6-07 (Info disclosure): `AssistantQuery` capped at 500/2000 chars, session key only
- T-6-08 (CSRF): `{% csrf_token %}` in chat form, Django middleware active
- T-6-09 (Elevation): Public access by design (D-4 in CONTEXT.md)

---

## Checkpoint Status

**Task 1 (auto):** Complete — commit 2d79518
**Task 2 (checkpoint:human-verify):** Template and nav link built and committed as part of Task 1. Awaiting human verification of live UI at http://localhost:8000/en/assistant/

---

## Self-Check: PASSED

Files verified present:
- apps/assistant/views.py — contains assistant_page, chat_view, assistant_stream
- apps/assistant/urls.py — contains page/chat/stream patterns
- apps/assistant/tests/test_views.py — 11 tests
- templates/assistant/chat.html — full chat UI
- templates/base.html — contains assistant:page nav link

Commits verified:
- 2d79518 — feat(06-03): chat views, SSE stream, crisis detection, rate limiting, nav link, chat template

46 assistant tests pass (venv activated).
