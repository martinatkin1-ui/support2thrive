---
phase: 6
slug: ai-assistant
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Django test runner (existing) |
| **Config file** | `config/settings/test.py` (uses SQLite, add SKIP_RAG_TESTS=True) |
| **Quick run command** | `python manage.py test apps.assistant --settings=config.settings.test` |
| **Full suite command** | `python manage.py test --settings=config.settings.test` |
| **Estimated runtime** | ~15 seconds (mocked RAG) |

**SQLite note:** All LightRAG/pgvector calls must be mocked in tests. Add `SKIP_RAG_TESTS = env.bool("SKIP_RAG_TESTS", default=True)` to test settings.

---

## Sampling Rate

- **After every task commit:** Run `python manage.py test apps.assistant --settings=config.settings.test`
- **After every plan wave:** Run `python manage.py test --settings=config.settings.test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 0 | RAG-001 | — | N/A | unit | `python manage.py test apps.assistant.tests.test_models --settings=config.settings.test` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 0 | RAG-002 | — | N/A | unit | `python manage.py test apps.assistant.tests.test_tasks --settings=config.settings.test` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | RAG-003 | T-6-01 | Crisis keywords trigger Samaritans response | unit | `python manage.py test apps.assistant.tests.test_crisis --settings=config.settings.test` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | RAG-004 | T-6-02 | Rate limit blocks 21st message | unit | `python manage.py test apps.assistant.tests.test_rate_limit --settings=config.settings.test` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 1 | RAG-005 | — | SSE returns text/event-stream | integration | `python manage.py test apps.assistant.tests.test_views --settings=config.settings.test` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | RAG-006 | — | PDF > 20MB rejected | unit | `python manage.py test apps.assistant.tests.test_models --settings=config.settings.test` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 2 | RAG-007 | — | Session history capped at 20 items | unit | `python manage.py test apps.assistant.tests.test_views --settings=config.settings.test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/assistant/tests/__init__.py` — create test package
- [ ] `apps/assistant/tests/test_crisis.py` — 15+ keyword assertions for crisis detection
- [ ] `apps/assistant/tests/test_rate_limit.py` — rate limiting unit tests (per-session count + per-minute throttle)
- [ ] `apps/assistant/tests/test_views.py` — chat view + SSE endpoint + session history cap
- [ ] `apps/assistant/tests/test_tasks.py` — Celery task mocking (mock insert_content_list)
- [ ] `apps/assistant/tests/test_models.py` — OrgDocument validation (file size ≤ 20MB, extension must be .pdf)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HTMX SSE streaming renders tokens progressively in browser | RAG-005 | Requires live browser + SSE connection | Load `/assistant/`, send message, confirm tokens appear incrementally |
| Obsidian vault sync picks up new .md files automatically | RAG-008 | Requires filesystem watcher + Redis running | Add new .md to vault, confirm `VaultDocument` created within 30s |
| Gemini 2.5 Flash responds with context from indexed org | RAG-003 | Requires live Gemini API key + pgvector | Ask "what does [org name] offer?", confirm answer references org |
| VectorExtension migration runs on Postgres | RAG-001 | Requires Postgres + pgvector Docker | `docker compose up db && python manage.py migrate` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
