# West Midlands Community Share Platform (WMCSP)

## Project Overview
Mobile-first Django web app connecting West Midlands community organizations for resource sharing, secure referrals, events, and AI-assisted navigation.

## Tech Stack
- **Backend**: Django 6.x + DRF
- **Database**: SQLite (dev) / PostgreSQL + pgvector (prod)
- **Frontend**: Django templates + HTMX + Tailwind CSS (CDN in dev)
- **Task Queue**: Celery + Redis
- **AI/RAG**: pgvector + sentence-transformers + Gemini 2.5 Flash

## Commands
```bash
# Activate virtual environment
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
