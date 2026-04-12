# West Midlands Community Share Platform (WMCSP)

## Project Overview
Mobile-first Django web app connecting West Midlands community organizations for resource sharing, secure referrals, events, and AI-assisted navigation. Serves vulnerable populations (prison leavers, homeless, people in recovery). PII security, audit logging, and 10-language i18n are first-class requirements.

## Tech Stack
- **Backend**: Django 6.0.x + Django REST Framework (DRF)
- **Database**: SQLite (dev) / PostgreSQL + pgvector (prod)
- **Frontend**: Django templates + HTMX + Tailwind CSS (CDN in dev)
- **Task Queue**: Celery + Redis
- **AI/RAG**: pgvector + sentence-transformers + Gemini 2.5 Flash

## Commands
```bash
# Activate virtual environment (Windows)
source venv/Scripts/activate

# Run dev server
python manage.py runserver

# Run tests
python manage.py test --settings=config.settings.test

# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Seed initial data
python manage.py seed_data

# Generate translation files
python manage.py makemessages -l pa -l pl -l ur -l ro -l bn -l gu -l ar -l so --ignore=venv
python manage.py compilemessages
```

## Project Structure
- `config/` - Django settings (base/dev/prod/test), URLs, Celery
- `apps/core/` - Base models (TimeStampedModel, Tag, GeographicArea, SupportStream)
- `apps/accounts/` - Custom User with roles, approval workflow
- `apps/organizations/` - Organization profiles, services
- `apps/events/` - Events, calendar, recurrence (Phase 2)
- `apps/referrals/` - Secure referral system with encrypted PII (Phase 4)
- `apps/services/` - Service category taxonomy (Phase 3)
- `apps/pathways/` - Prison leavers & homeless sections (Phase 5)
- `apps/assistant/` - RAG-based AI assistant (Phase 6)
- `apps/newsfeed/` - Auto-scraped + manual news (Phase 4b)
- `apps/audit/` - Hash-chained audit log (Phase 4)
- `apps/notifications/` - Email/SMS notifications (Phase 4)
- `templates/` - Django templates (public/, portal/, volunteer/, accounts/)

## User Roles
- `public` - Browse, view events/orgs, use AI assistant
- `volunteer` - Create referrals to any org, view own referrals
- `org_manager` - Manage org profile/events/services, approve volunteers
- `admin` - Full access

## i18n
10 languages: en, pa (Punjabi), pl (Polish), ur (Urdu/RTL), ro (Romanian), bn (Bengali), gu (Gujarati), ar (Arabic/RTL), zh-hans (Chinese), so (Somali)

## Environment
Settings auto-import from `config/settings/local.py` which imports `dev.py`. Production uses `prod.py`.

---

## Dev Tools

Five tools extend Claude Code for this project. Each operates at a distinct layer of the workflow — see **Agentic Hierarchy** below for how they interlock.

### GSD Pro (Workflow Governor)
Spec-driven workflow system. Manages phase progression, context state, and the 5-phase development cycle across sessions: Initialize → Discuss → Plan → Execute → Verify.
- **Repo:** https://github.com/itsjwill/gsd-pro
- **Install (global, run once):**
  ```bash
  npx get-shit-done-cc@latest --claude --global
  ```
- **Install (this project only):**
  ```bash
  npx get-shit-done-cc@latest --claude
  ```
- **Owns:** `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md` in project root

### Claude Mem (Knowledge Layer)
Plugin that captures coding sessions into a persistent, compressed knowledge base. Automatic — activates on session start/end via lifecycle hooks. Search past work with `/mem-search`. View memories at `http://localhost:37777`.
- **Repo:** https://github.com/thedotmack/claude-mem
- **Installed:** `~/.claude/plugins/marketplaces/thedotmack/` (plugin scope: user)
- **Start worker:** `npx claude-mem start`
- **Reinstall:** `npx claude-mem install`

### UI/UX Pro Max (Design Intelligence)
Design system skill with 67 UI styles, 161 colour palettes, 57 font pairings, 99 UX guidelines, and 25 chart types. Auto-activates for UI tasks; invoke manually with `/ui-ux-pro-max`. Tailored to Django templates + Tailwind CSS + HTMX for this project.
- **Repo:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
- **Installed:** `.claude/skills/ui-ux-pro-max/` (project scope)
- **Used by:** @frontend for all template and design-system work
- **Reinstall:** `npx uipro-cli init --ai claude`

### Superpowers Marketplace (Skills Layer)
Curated Claude Code plugin catalog. Provides installable skills and workflow patterns injected into specialist agents.
- **Repo:** https://github.com/obra/superpowers-marketplace
- **Installed:** `~/.claude/plugins/marketplaces/superpowers-marketplace/` (plugin scope: user, v5.0.7)
- **Reinstall:** `claude plugin marketplace add obra/superpowers-marketplace && claude plugin install superpowers@superpowers-marketplace`
- **Used by:** @tester (TDD patterns), @frontend (HTMX patterns), @privacy_security (security review)

### Awesome Claude Code (Reference Index)
Curated index of 100+ Claude Code tools, skills, hooks, and slash-commands. Consult when the existing toolkit has a gap.
- **Repo:** https://github.com/hesreallyhim/awesome-claude-code
- Reference only — not installed as a tool.

---

## Agentic Hierarchy

All development runs through four layers. Work flows downward only — each layer has a single responsibility.

```
┌──────────────────────────────────────────────────┐
│  LAYER 0 — WORKFLOW GOVERNOR                     │
│  GSD Pro  ·  STATE.md  ·  ROADMAP.md             │
│  Owns: phase progression, task context, gates    │
└────────────────────┬─────────────────────────────┘
                     │ current phase + task
┌────────────────────▼─────────────────────────────┐
│  LAYER 1 — KNOWLEDGE                             │
│  Claude Mem  ·  knowledge/  ·  daily/            │
│  Surfaces: past decisions, patterns, Q&A         │
└────────────────────┬─────────────────────────────┘
                     │ enriched context
┌────────────────────▼─────────────────────────────┐
│  LAYER 2 — ORCHESTRATOR  (Haiku)                 │
│  Cost-aware router — scores complexity (1–10),   │
│  selects model tier, delegates to specialist     │
└──────┬──────┬──────┬──────┬──────────────────────┘
       ↓      ↓      ↓      ↓
┌─────────────────────────────────────────────────┐
│  LAYER 3 — SPECIALIST AGENTS                    │
│  @django_backend  @privacy_security  @frontend  │
│  @tester  @integration  @architect  @researcher │
└────────────────────┬────────────────────────────┘
                     │ skills injected on demand
┌────────────────────▼────────────────────────────┐
│  LAYER 4 — SKILLS                               │
│  Superpowers Marketplace  ·  UI/UX Pro Max      │
│  TDD · HTMX · security-review · design-system  │
└─────────────────────────────────────────────────┘
```

### Specialist Agent Roster

| Agent | Model | Scope |
|---|---|---|
| @django_backend | Sonnet | Models, views, APIs, migrations, service layer |
| @privacy_security | Sonnet | PII encryption, GDPR, OWASP, audit log, auth hardening |
| @frontend | Haiku | Django templates, HTMX partials, Tailwind CSS, i18n strings — uses UI/UX Pro Max for all design decisions |
| @tester | Haiku | pytest, coverage, fixtures, E2E |
| @integration | Sonnet | Celery tasks, Redis, Gemini 2.5 Flash API, external services |
| @architect | Sonnet | Phase schema design (requires user approval to proceed) |
| @researcher | Sonnet | Domain research — social services, safeguarding law, org data |

### Routing Rules (Complexity → Model)

| Score | Criteria | Route |
|---|---|---|
| 1–3 | Read/search, typo fix, single template edit | Haiku directly |
| 4–5 | Single-file feature, simple test, translation string | Haiku · @frontend or @tester |
| 6–7 | Multi-file feature, migration, API endpoint | Sonnet · @django_backend or @integration |
| 8–9 | PII field, auth change, audit log, encrypted referral | Sonnet · @privacy_security mandatory |
| 10 | New phase kickoff, breaking schema change | Sonnet · @architect + explicit user approval |

### WMCSP-Specific Routing Rules
- Any change touching `apps/referrals/`, `apps/audit/`, or encrypted fields → **@privacy_security reviews first**
- Any new template or user-facing string → **@frontend adds `{% trans %}` wrappers before commit**
- Celery tasks, Redis pub/sub, Gemini API integration → **@integration owns the service layer**
- New phase kickoff → **@architect proposes schema → user approves → @django_backend implements**

### Session Flow

**Start**
```
GSD Pro  →  loads STATE.md, identifies phase + next task
Claude Mem  →  surfaces relevant knowledge/ entries
Orchestrator  →  scores task, selects agent + model tier
```

**Execute**
```
Specialist agent works · Superpowers skill injected if pattern matches
@privacy_security consulted on any data-touching change (score ≥ 8)
```

**End**
```
python manage.py test --settings=config.settings.test   # must pass
ruff check apps/ -q                                      # must be clean
git commit  (feat|fix|refactor|chore: message)
Claude Mem  →  compiles session into knowledge/
GSD Pro     →  updates STATE.md, advances phase if gate criteria met
```

### Phase Gate Protocol

Before advancing between build phases:
1. @tester — full test suite passes
2. @privacy_security — new data flows reviewed for GDPR compliance
3. @architect — schema is stable and documented
4. User explicitly approves phase transition in GSD Pro
5. Claude Mem writes `knowledge/concepts/phase-N-complete.md`

### Build Phase Reference

| Phase | Status | Scope | Lead Agents |
|---|---|---|---|
| 1 | Done | Foundation — auth, orgs, i18n | @django_backend |
| 2 | Next | Events, calendar, recurrence | @django_backend, @frontend |
| 3 | — | Service category taxonomy | @django_backend, @frontend |
| 4 | — | Referrals (encrypted PII), audit log, notifications, newsfeed | @privacy_security, @django_backend, @integration |
| 5 | — | Prison leavers & homeless pathways | @django_backend, @researcher |
| 6 | — | RAG AI assistant (pgvector + Gemini 2.5 Flash) | @integration, @architect |
