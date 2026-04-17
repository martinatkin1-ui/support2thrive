# Support2Thrive (S2T) — Current State

**Last updated:** 2026-04-13
**Current phase:** 6 — AI Assistant
**Previous phase:** 5 — Pathways + Design System Rectification (COMPLETE ✅)

---

## Phase 1 Audit — COMPLETE ✅

### What Was Built
| Component | File(s) | Status |
|---|---|---|
| TimeStampedModel, Tag, GeographicArea, SupportStream | `apps/core/models.py` | ✅ |
| Custom User with roles + approval workflow | `apps/accounts/models.py` | ✅ |
| RegistrationForm + register/login/profile views | `apps/accounts/views.py`, `forms.py` | ✅ |
| Organization + OrganizationService models | `apps/organizations/models.py` | ✅ |
| Org list + detail views (public) | `apps/organizations/views.py` | ✅ |
| DRF API: org list + detail | `apps/organizations/api_views.py`, `serializers.py` | ✅ |
| Base template (Tailwind, HTMX, RTL, lang switcher) | `templates/base.html` | ✅ |
| Public templates: home, org list, org detail | `templates/public/` | ✅ |
| Account templates: login, register, profile | `templates/accounts/` | ✅ |
| i18n: 10 languages, RTL for ar/ur | `locale/`, `config/settings/base.py` | ✅ |
| Seed data: 6 orgs, 15 streams, 8 areas | `apps/core/management/commands/seed_data.py` | ✅ |
| Initial migrations | `apps/*/migrations/0001_initial.py` | ✅ |
| Tests: 24 passing | `apps/accounts/tests.py`, `apps/organizations/tests.py` | ✅ |
| Docker-compose | `docker-compose.yml` | ✅ |

---

## Phase 2 Audit — COMPLETE ✅

### What Was Built
| Component | File(s) | Status |
|---|---|---|
| Region model (multi-region scalability) | `apps/core/models.py` | ✅ |
| Region admin with branding fieldsets | `apps/core/admin.py` | ✅ |
| Organization region FK + data migration | `apps/organizations/models.py`, `migrations/0003_*` | ✅ |
| Event model (RFC 5545 rrule, slugged, region-scoped) | `apps/events/models.py` | ✅ |
| EventRecurrenceRule model | `apps/events/models.py` | ✅ |
| EventOccurrence model (pre-generated, indexed) | `apps/events/models.py` | ✅ |
| Event admin with inline occurrences | `apps/events/admin.py` | ✅ |
| Occurrence generation service (lazy rrule iteration) | `apps/events/services.py` | ✅ |
| Celery tasks: generate occurrences, scrape events | `apps/events/tasks.py` | ✅ |
| Public calendar views (HTMX month navigation) | `apps/events/views.py` | ✅ |
| iCal feed (platform + per-org) | `apps/events/ical.py`, `views.py` | ✅ |
| Org manager event CRUD portal | `apps/events/views.py` | ✅ |
| Public templates: event list, detail, partial | `templates/public/events/` | ✅ |
| Portal templates: event list, form | `templates/portal/events/` | ✅ |
| URL config wired with i18n_patterns | `apps/events/urls.py`, `config/urls.py` | ✅ |
| Nav updated in base.html | `templates/base.html` | ✅ |
| Tests: 47 passing (all) | `apps/events/tests.py` | ✅ |

### Key Architecture Decisions Made
- **Multi-region**: `Region` model as top-level scope; all content FKs to Region. No URL changes for MVP — routing added when second region deploys.
- **Recurrence**: RFC 5545 rrule strings stored in DB, parsed by `dateutil.rrulestr()` with lazy iteration (no materialising infinite lists).
- **Occurrences**: Pre-generated `EventOccurrence` rows in rolling 12-month window — queryable, indexed, HTMX-navigable.
- **Calendar UI**: Agenda list (mobile-first) + optional month grid toggle.

### Known Issues / Carry-forwards
- `axes.W006`: low priority, fix Phase 4 auth hardening
- Celery beat schedule not yet registered for occurrence generation / scraping tasks
- Portal nav link not yet in base.html sidebar for org_managers

---

## Phase 3 Audit — COMPLETE ✅

### What Was Built
| Component | File(s) | Status |
|---|---|---|
| OrgOnboardingState model (5-step wizard, completion score) | `apps/organizations/models.py` | ✅ |
| OnboardingRedirectMiddleware (gates portal until complete) | `apps/organizations/middleware.py` | ✅ |
| Wizard views: step routing, progress bar, back/next | `apps/organizations/views.py` | ✅ |
| Step 1 — About: description, logo, website, contact | portal templates | ✅ |
| Step 2 — Services: ServiceCategory picker | portal templates | ✅ |
| Step 3 — Referral Config: form fields, delivery channels | portal templates | ✅ |
| Step 4 — Scraping Config: events_page_url, news_page_url | portal templates | ✅ |
| Step 5 — Review & Publish: confirm → org active | portal templates | ✅ |
| ServiceCategory model (hierarchical, region-aware, icon) | `apps/services/models.py` | ✅ |
| OrganizationService linked to ServiceCategory | `apps/organizations/models.py` | ✅ |
| Portal dashboard with completeness score bar | `templates/portal/` | ✅ |
| Admin: manually mark/reset onboarding | `apps/organizations/admin.py` | ✅ |
| Tests: +46 (total 93) | `apps/organizations/tests.py` | ✅ |

---

## Phase 4 Audit — COMPLETE ✅

### What Was Built
| Component | File(s) | Status |
|---|---|---|
| Referral model (UUID ref, 6-status FSM, priority, consent) | `apps/referrals/models.py` | ✅ |
| ReferralFormField (15 field types incl. PII: NHS, NI, DBS) | `apps/referrals/models.py` | ✅ |
| ReferralDelivery (multi-channel: inbox/email/CSV/print/webhook) | `apps/referrals/models.py` | ✅ |
| ReferralStatusHistory (append-only FSM audit trail) | `apps/referrals/models.py` | ✅ |
| AuditEntry (SHA-256 hash-chained tamper-evident log) | `apps/audit/models.py` | ✅ |
| Fernet encryption (AES-128-CBC + HMAC-SHA256) for PII at rest | `apps/referrals/encryption.py` | ✅ |
| create_referral() service: store → encrypt → queue delivery | `apps/referrals/services.py` | ✅ |
| Celery delivery engine: email (3 retries), webhook (5 retries, HMAC-signed) | `apps/referrals/tasks.py` | ✅ |
| Escalation: Celery beat 24h/48h unacknowledged alerts | `apps/referrals/tasks.py` | ✅ |
| Portal referral inbox + detail + acknowledge/status update | `apps/referrals/views.py` | ✅ |
| Public referral form with GDPR consent | `templates/public/` | ✅ |
| Notifications app: stubbed (model shell) | `apps/notifications/` | ✅ |
| Newsfeed app: stubbed (model shell) | `apps/newsfeed/` | ✅ |
| Tests: +39 (total 132) | `apps/referrals/tests.py` | ✅ |

### Key Architecture Decisions Made
- **No-loss guarantee**: Referral always written to DB first; delivery is async — failure cannot lose the referral.
- **Per-org encryption key** derives from platform SECRET_KEY in dev; separate key required in production.
- **GDPR consent** checkbox always appended to every referral form; cannot be removed by org managers.
- **Notifications/Newsfeed**: skeleton apps created, full implementation deferred to a future phase.

---

## Phase 5 Audit — COMPLETE ✅

### What Was Built
| Component | File(s) | Status |
|---|---|---|
| Pathway model (region-scoped, audience: prison/homeless/both) | `apps/pathways/models.py` | ✅ |
| PathwaySection model (grouped content blocks, icon, intro) | `apps/pathways/models.py` | ✅ |
| PathwayGuideItem model (steps, external/org links, urgency flag) | `apps/pathways/models.py` | ✅ |
| Seed data: 2 pathways × 5 sections with real WM content | `apps/pathways/management/` | ✅ |
| Public views: pathway_list + pathway_detail | `apps/pathways/views.py` | ✅ |
| Templates: list (hero cards), detail (sticky TOC, amber urgency, Phase 6 AI placeholder) | `templates/public/pathways/` | ✅ |
| Design system overhaul: Figtree/Noto Sans, amber CTAs (#F59E0B), WCAG AAA contrast | `design-system/MASTER.md`, `templates/base.html` | ✅ |
| Icon replacement: emoji → Heroicons SVGs (11 templates) | `templates/` | ✅ |
| Accessibility: fieldset/legend, min-h-[44px] touch targets, ARIA labels | `templates/` | ✅ |
| Tests: +17 (total 139) | `apps/pathways/tests.py` | ✅ |

### Test Results (last run: 2026-04-13)
```
Ran 139 tests in 1.193s — OK
```

---

## Phase 6 — AI Assistant 🔄 STARTING NOW

### Goal
A chat-based assistant that helps any user navigate services, powered by semantic search over all platform content (orgs, services, events, pathways, news).

### Architecture
```
User query → embedding (sentence-transformers)
           → pgvector similarity search over indexed content
           → top-k results as context
           → Gemini 2.5 Flash generates response
           → streamed back via HTMX
```

### Current State
- `apps/assistant/` exists as a skeleton (empty models, no views/urls/migrations)
- pgvector not yet configured (dev uses SQLite — needs fallback/dev strategy)
- Gemini API not yet integrated

### Next Actions (in order)
1. Decide dev RAG strategy: real pgvector (Docker) vs. SQLite fallback vs. mock embeddings
2. `ContentEmbedding` model: content_type, object_id, vector, text_snippet, updated_at
3. Indexing pipeline: Celery task embeds org/service/event/pathway/news content on save
4. `Conversation` + `ConversationMessage` models: session-scoped, rate-limited
5. Chat view + HTMX streaming endpoint
6. Gemini 2.5 Flash RAG pipeline: retrieve → build context → generate
7. Rate limiting per user (daily token budget or message count)
8. Tests + gate

---

## Dev Environment

```bash
# Activate venv (Windows)
source venv/Scripts/activate

# Run dev server
python manage.py runserver

# Run tests
python manage.py test --settings=config.settings.test

# Start Claude Mem worker (persistent memory)
npx claude-mem start

# GSD workflow commands
/gsd-next          # What to work on next
/gsd-progress      # Current progress summary
/gsd-plan-phase    # Plan the current phase in detail
/gsd-execute-phase # Execute current phase tasks
/gsd-verify-work   # Verify completed work
```

## Tool Status
| Tool | Status | Notes |
|---|---|---|
| GSD Pro v1.34.2 | ✅ Active | 68 skills, 24 agents in `~/.claude/` |
| Claude Mem v12.1.0 | ✅ Active | Plugin enabled, run `npx claude-mem start` for worker |
| Superpowers v5.0.7 | ✅ Active | Plugin enabled |
| UI/UX Pro Max v2.5.0 | ✅ Active | Project skill at `.claude/skills/ui-ux-pro-max/` |
