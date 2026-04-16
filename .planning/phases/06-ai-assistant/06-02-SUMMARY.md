---
phase: 06-ai-assistant
plan: "02"
subsystem: assistant
tags: [celery, indexing, signals, pdf-processing, admin, management-command, rag, lightrag]
dependency_graph:
  requires:
    - apps/assistant/models.py (OrgDocument, Conversation — from Plan 06-01)
    - apps/assistant/rag_service.py (get_rag_instance, build_org_content_list, build_pathway_content_list — from Plan 06-01)
  provides:
    - apps/assistant/tasks.py (index_organization, index_pathway, index_org_document)
    - apps/assistant/services.py (process_org_document)
    - apps/assistant/signals.py (register_signals — post_save wiring)
    - apps/assistant/apps.py (AssistantConfig.ready — registers signals)
    - apps/assistant/admin.py (OrgDocumentAdmin, OrgDocumentInline, AssistantQueryAdmin, ConversationAdmin)
    - apps/organizations/admin.py (OrgDocumentInline added to OrganizationAdmin)
    - apps/assistant/management/commands/index_all_content.py (bootstrap command)
  affects:
    - apps/organizations/admin.py (OrgDocumentInline added)
    - apps/core/views.py (root_language_redirect added — missing from worktree commit)
tech_stack:
  added: []
  patterns:
    - shared_task(bind=True, max_retries=3) with exponential backoff (referrals/tasks.py pattern)
    - asyncio.run() inside Celery task to call async LightRAG APIs from sync worker
    - deferred import of pymupdf4llm inside function (not installed in test env — mocked via sys.modules)
    - register_signals() pattern in AppConfig.ready() to avoid AppRegistryNotReady
    - sys.modules injection for mocking uninstalled packages in tests
key_files:
  created:
    - apps/assistant/tasks.py
    - apps/assistant/services.py
    - apps/assistant/signals.py
    - apps/assistant/management/__init__.py
    - apps/assistant/management/commands/__init__.py
    - apps/assistant/management/commands/index_all_content.py
  modified:
    - apps/assistant/apps.py (added ready())
    - apps/assistant/admin.py (written from empty stub)
    - apps/assistant/tests/test_tasks.py (expanded from 2 stubs to 7 tests)
    - apps/organizations/admin.py (OrgDocumentInline added)
    - apps/core/views.py (root_language_redirect added — Rule 3 fix)
decisions:
  - "pymupdf4llm imported deferred (inside function) so services.py loads without the package installed"
  - "sys.modules injection used in tests to mock pymupdf4llm since @patch requires module-level attribute"
  - "register_signals() function pattern (not module-level receivers) prevents AppRegistryNotReady"
metrics:
  duration: "~25 minutes"
  completed: "2026-04-16T09:30:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 7
  files_modified: 5
---

# Phase 6 Plan 02: Indexing Pipeline — Celery Tasks, Signals, Admin, Management Command

**One-liner:** Three Celery indexing tasks (org/pathway/PDF) with asyncio.run() bridge, post_save signal wiring on all content models, OrgDocumentInline in admin, and index_all_content bootstrap command.

---

## What Was Built

### Task 1: Celery Indexing Tasks + PDF Processing Service (commit 561c6ad)

**apps/assistant/tasks.py** — three tasks following `apps/referrals/tasks.py` pattern exactly:

| Task | Trigger | Content Source | Rate Limit |
|------|---------|---------------|------------|
| `index_organization` | post_save on Organization/OrganizationService | `build_org_content_list()` | 2/m |
| `index_pathway` | post_save on Pathway/PathwaySection/PathwayGuideItem | `build_pathway_content_list()` | 2/m |
| `index_org_document` | post_save on OrgDocument | `process_org_document()` service | none |

All tasks: `bind=True`, `max_retries=3`, exponential backoff (`countdown * 2**retries`), `logger.exception()`.

**apps/assistant/services.py** — `process_org_document(document_id)`:
- Deferred `import pymupdf4llm` inside function (not installed in test env)
- `pymupdf4llm.to_markdown()` extracts PDF to markdown
- `_split_text()` chunks at 2000 chars, breaking at newlines
- `asyncio.run(_index())` calls `rag.insert_content_list()` with org-scoped doc_id
- On success: sets `indexed_at = timezone.now()`, clears `index_error`
- On failure: caps error message at 500 chars, saves to `index_error`, re-raises for Celery retry

**apps/assistant/tests/test_tasks.py** — 7 tests:
- `BuildOrgContentListTest`: required keys, org name in text, missing org returns []
- `IndexOrganizationTaskTest`: asyncio.run called, empty content_list skips RAG
- `ProcessOrgDocumentTest`: indexed_at set on success, index_error set on failure

### Task 2: Signals, apps.py, Admin, Management Command (commit df4f65c)

**apps/assistant/signals.py** — `register_signals()` function (called from `ready()`):

| Signal | Sender | Task Dispatched |
|--------|--------|----------------|
| post_save | Organization | `index_organization.delay(pk)` |
| post_save | OrganizationService | `index_organization.delay(organization_id)` |
| post_save | Pathway | `index_pathway.delay(pk)` |
| post_save | PathwaySection | `index_pathway.delay(pathway_id)` |
| post_save | PathwayGuideItem | `index_pathway.delay(section.pathway_id)` |
| post_save | OrgDocument | `index_org_document.delay(pk)` (only if `instance.file` set) |

All signal handlers catch exceptions with `logger.exception()` — signal dispatch failures never crash the save.

**apps/assistant/apps.py** — `AssistantConfig.ready()` calls `register_signals()`.

**apps/assistant/admin.py**:
- `OrgDocumentInline`: tabular inline for Organization admin, `indexed_at`/`index_error` readonly
- `OrgDocumentAdmin`: list display with `indexed_status` boolean display, fieldsets with collapsible indexing status
- `AssistantQueryAdmin`: read-only (no add permission), query text truncated at 80 chars
- `ConversationAdmin`: read-only (no add permission)

**apps/organizations/admin.py** — `OrgDocumentInline` added to `OrganizationAdmin.inlines`.

**apps/assistant/management/commands/index_all_content.py**:
- `--dry-run`: prints what would be indexed without dispatching
- `--orgs-only`: skips pathways
- `--pathways-only`: skips organisations
- Default: indexes all active orgs + all published pathways via `.delay()` calls

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] root_language_redirect missing from apps/core/views.py**
- **Found during:** Task 1 — running tests failed with `ImportError: cannot import name 'root_language_redirect'`
- **Issue:** `config/urls.py` in the worktree's base commit references `root_language_redirect` from `apps.core.views`, but the function was not present in that commit's `views.py`
- **Fix:** Added `root_language_redirect` view to `apps/core/views.py` (matches implementation in main project)
- **Files modified:** `apps/core/views.py`
- **Commit:** 561c6ad

**2. [Rule 1 - Bug] pymupdf4llm module-level import blocks services.py loading**
- **Found during:** Task 1 — `@patch("apps.assistant.services.pymupdf4llm")` failed with `AttributeError: module 'apps.assistant' has no attribute 'services'` because top-level `import pymupdf4llm` raised `ModuleNotFoundError` (package not installed in test env)
- **Fix:** Moved `import pymupdf4llm` to inside `process_org_document()` function (deferred import). Updated tests to inject mock via `sys.modules["pymupdf4llm"]` in `setUp()` instead of `@patch` decorator
- **Files modified:** `apps/assistant/services.py`, `apps/assistant/tests/test_tasks.py`
- **Commit:** 561c6ad

---

## Test Results

| Test Module | Tests | Status |
|---|---|---|
| `test_tasks.py` | 7 | PASS |
| `test_models.py` | 3 | PASS |
| `test_crisis.py` | 20 | PASS |
| `test_rate_limit.py` | 5 | PASS |
| `test_views.py` | 2 | PASS |
| **Assistant total** | **37** | **PASS** |
| **Full suite** | **176** | **PASS** |

---

## Known Stubs

None introduced in this plan. All indexed_at/index_error fields are fully wired.

---

## Threat Surface Scan

No new network endpoints introduced. Post-save signal dispatch is fire-and-forget with exception catch — signal failures cannot crash saves (T-6-13 mitigation: only org_id logged, not content). Rate limit on `index_organization` and `index_pathway` tasks (`rate_limit="2/m"`) mitigates T-6-03c (Gemini API flooding). OrgDocument admin has `indexed_at` and `index_error` as `readonly_fields` (T-6-14).

---

## Self-Check: PASSED
