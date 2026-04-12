# WMCSP — Current State

**Last updated:** 2026-04-11
**Current phase:** 3 — Org Onboarding & Service Taxonomy
**Previous phase:** 2 — Events & Calendar (COMPLETE ✅)

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

### Test Results (last run: 2026-04-11)
```
Ran 47 tests in 1.500s — OK
```

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

## Phase 3 — Org Onboarding & Service Taxonomy 🔄 STARTING NOW

### Goal
First-time org managers go through a guided onboarding wizard that sets up their full profile, services, referral form preferences, and delivery settings. This replaces the current manual admin-only workflow and gates access to the portal until onboarding is complete.

### Active Sprint: M3.1 — Onboarding Wizard

**Entry criteria — all met:**
- [x] Phase 2 tests passing (47/47)
- [x] Region model in place (scalability foundation)
- [x] Org model has all required fields for onboarding

**Next actions (in order):**
1. Design onboarding flow + step model (`apps/organizations/onboarding.py`) — @architect
2. `OrgOnboardingState` model: tracks which steps are complete per org — @django_backend
3. Step 1: About page (description, logo, website, contact) — @frontend + @django_backend
4. Step 2: Services offered (ServiceCategory picker) — @django_backend + @frontend
5. Step 3: Referral preferences (form fields, delivery channels, CRM) — @django_backend
6. Step 4: Scraping config (events_page_url, news_page_url) — @django_backend
7. Step 5: Review & publish — @frontend
8. `ServiceCategory` model (hierarchical, with seed data) — @django_backend
9. Tests — @tester
10. Phase 3 gate: @privacy_security review of referral config storage

---

## Phase 4 — Referrals, Delivery & No-Loss Guarantee ⬜

See ROADMAP.md for full milestone breakdown.

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
