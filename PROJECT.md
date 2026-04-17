# Support2Thrive (S2T)

## What This Is
**Support2Thrive** is a mobile-first Django web application that connects West Midlands community organisations so vulnerable people — prison leavers, people experiencing homelessness, those in addiction recovery — can find the right support quickly. Organisations share events, accept referrals, publish services, and the platform provides an AI-assisted navigation layer across all of it.

## Problem Being Solved
West Midlands organisations (Recovery Near You, The Good Shepherd, Black Country Healthcare NHS, Wolverhampton Council, Rethink, and others) operate in silos. Frontline workers and service users cannot easily discover what's available, refer across organisations, or track whether a referral was acted on. Vulnerable people fall through the gaps.

## Who This Serves
- **People seeking help** — prison leavers, homeless, those in recovery, carers, elderly
- **Volunteers & frontline workers** — creating and tracking referrals
- **Organisation managers** — managing their profile, services, and events
- **Platform admins** — approving users, maintaining data quality

## Core Organisations (seeded)
1. Recovery Near You — addiction & recovery, Wolverhampton
2. The Good Shepherd — homelessness & food, Wolverhampton
3. The Local NHS / Black Country Healthcare NHS FT — health & mental health
4. Wolverhampton Council — housing, benefits, social care
5. Rethink Mental Illness — mental health peer support

## Key Constraints
- **PII security**: Referral data is sensitive — encrypted at rest, audit-logged, GDPR-compliant
- **Mobile-first**: Primary users access via phone. All UI must work on small screens
- **i18n**: 10 languages including RTL (Arabic, Urdu) for West Midlands communities
- **No native app**: Responsive web only — reduces maintenance burden
- **Self-register + approval**: Volunteers and org managers require admin approval before portal access

## Tech Stack
- Django 6.0.x + DRF · SQLite (dev) / PostgreSQL + pgvector (prod)
- Django templates + HTMX + Tailwind CSS (CDN in dev)
- Celery + Redis · Gemini 2.5 Flash · sentence-transformers

## Agentic Workflow
All development follows the 5-layer hierarchy defined in CLAUDE.md:
GSD Pro (workflow) → Claude Mem (knowledge) → Orchestrator (routing) → Specialist Agents → Superpowers + UI/UX Pro Max (skills)
