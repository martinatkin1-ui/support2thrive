# Support2Thrive (S2T) — Roadmap

## Phase Overview

| Phase | Name | Status | Key Deliverable |
|---|---|---|---|
| 1 | Foundation | ✅ COMPLETE | Django project, auth, orgs, i18n, seed data |
| 2 | Events & Calendar | ✅ COMPLETE | Public event calendar with recurrence + iCal + multi-region |
| 3 | Org Onboarding & Service Taxonomy | 🔄 IN PROGRESS | Guided onboarding wizard, service categories, referral config |
| 4 | Referrals & No-Loss Delivery | ⬜ NEXT | Custom referral forms, multi-channel delivery, audit chain |
| 5 | Pathways | ⬜ Planned | Prison leavers & homeless dedicated portal sections |
| 6 | AI Assistant | ⬜ Planned | pgvector RAG + Gemini 2.5 Flash chat |

---

## Phase 1 — Foundation ✅ COMPLETE

### Delivered
- [x] Django 6.0.x project structure with multi-settings (base/dev/prod/test)
- [x] Custom User model: roles (public/volunteer/org_manager/admin), approval workflow, preferred language
- [x] Organization model: full contact info, geo-coords, taxonomy, referral config, scraping URLs, RAG timestamp, translated descriptions
- [x] OrganizationService model: access model, age range, eligibility notes, tags
- [x] Core models: TimeStampedModel, Tag, GeographicArea, SupportStream (15 streams seeded)
- [x] Public views: home, org list (filterable by stream/area), org detail
- [x] Accounts: register, login, logout, profile
- [x] REST API: organization list + detail (DRF + pagination)
- [x] Base template: Tailwind CDN, HTMX, RTL support, mobile menu, language switcher
- [x] Templates: home, org list, org detail, login, register, profile
- [x] i18n: 10 languages configured, `{% trans %}` throughout
- [x] Seed data: 6 real WM orgs, 15 support streams, 8 geographic areas
- [x] Tests: 24 tests, all passing
- [x] docker-compose.yml for production stack

---

## Phase 2 — Events & Calendar ✅ COMPLETE

### Delivered
- [x] `Region` model — top-level geographic scope enabling white-label multi-region deployment
- [x] Region FK on Organization + data migration (West Midlands region seeded)
- [x] `Event` model — org-scoped, region-scoped, RFC 5545 rrule support, is_published, booking_url, is_free, is_online
- [x] `EventRecurrenceRule` model — rrule string, dtstart, duration_minutes, until, count, exceptions (JSON)
- [x] `EventOccurrence` model — pre-generated, indexed on (event, start), unique constraint, per-occurrence overrides
- [x] Occurrence generation service — lazy rrule iteration (window 12 months), idempotent via get_or_create
- [x] Celery tasks: generate occurrences per event/region/all, weekly scraper skeleton
- [x] Public calendar — agenda list + grid toggle, HTMX month navigation, stream filter
- [x] Event detail — upcoming occurrences list, booking CTA, location/online display, iCal link
- [x] iCal feed — `/events/calendar.ics` (all) and `/events/org/<slug>/calendar.ics` (per-org)
- [x] Org manager portal — event CRUD, recurrence editor, publish toggle, delete with confirm
- [x] Tests: 47/47 passing (model, service, view, iCal)

### Gate Criteria — All Met
- [x] All 47 tests passing
- [x] No PII in events (no GDPR concern at this phase)
- [x] Multi-region architecture validated

---

## Phase 3 — Org Onboarding & Service Taxonomy 🔄 IN PROGRESS

### Goal
New org managers complete a step-by-step onboarding wizard before accessing the portal. This captures everything needed to make the org useful on the platform: their profile, services, referral form design, preferred delivery channels, and scraping config. A `ServiceCategory` hierarchy (extending the existing SupportStream flat list) provides a navigable taxonomy for the public.

### Milestones

#### M3.1 — Onboarding Wizard Framework
- [ ] `OrgOnboardingState` model: org FK (OneToOne), completed steps (JSONField), is_complete BooleanField, started_at, completed_at
- [ ] Middleware or decorator: redirect org_managers with incomplete onboarding to `/portal/onboarding/` on every portal request
- [ ] Wizard base view: step routing, progress bar, back/next navigation
- [ ] Step 1 — **About**: short_description, description (rich text preview), logo upload, website, contact_email, contact_phone, social links
- [ ] Step 2 — **Services**: pick from ServiceCategory tree + free-text service descriptions; link to OrganizationService records
- [ ] Step 3 — **Referral Config**: choose referral form fields (custom builder), set delivery channel preferences (see Phase 4 for full delivery implementation)
- [ ] Step 4 — **Scraping Config**: events_page_url, news_page_url (optional)
- [ ] Step 5 — **Review & Publish**: summary of all steps, confirm to set org status=active + onboarding complete
- [ ] Admin: manually mark onboarding complete / reset steps
- [ ] Tests

#### M3.2 — Service Category Taxonomy
- [ ] `ServiceCategory` model: name, slug, parent FK (self-referential), description, icon, display_order, region FK (allows region-specific categories)
- [ ] `OrganizationService` updated: link to `ServiceCategory` (alongside existing SupportStream)
- [ ] Public browse-by-category view: HTMX expandable tree, shows orgs + services per category
- [ ] Seed initial category tree from existing 15 SupportStreams
- [ ] Admin management with drag-to-reorder (or display_order integer)
- [ ] Tests

#### M3.3 — Org Profile Completeness
- [ ] Completeness score on org model (0–100%): weighted field presence check
- [ ] Visual completeness indicator in portal dashboard
- [ ] "Nudge" banner when completeness < 80%
- [ ] Tests + gate

---

## Phase 4 — Referrals & No-Loss Delivery ⬜

### Goal
Enable volunteers and the public to make secure referrals to organisations. Custom referral forms (designed by each org during onboarding) collect only what the org needs. All referrals are stored in the platform and delivered via the channel the org prefers — with guaranteed no-loss: every referral is acknowledged, retried on failure, and escalated if unread.

### Architecture Overview
```
Referral submitted → stored in DB (always)
                   → queued for delivery (Celery)
                   → delivered via chosen channel(s)
                   → delivery status tracked
                   → unacknowledged escalation (24h/48h alerts)
```

### Milestones

#### M4.1 — Custom Referral Form Builder
- [ ] `ReferralFormField` model: org FK, field_type (text/email/phone/date/select/checkbox/file/id_number/nhs_number/ni_number/dob/postcode/textarea/consent), label, help_text, is_required, display_order, options (JSON for select/checkbox), is_pii (flags field for encryption)
- [ ] Field types include identity documents: Passport, DBS reference, NI number, NHS number — each stored with `is_pii=True`
- [ ] GDPR consent checkbox always appended (cannot be removed by org)
- [ ] Form builder UI: drag-to-reorder fields, add/remove, field type picker, preview mode
- [ ] Form preview renders as the public-facing referral form
- [ ] Tests

#### M4.2 — Referral Submission & Encrypted Storage
- [ ] `Referral` model:
  - `reference_number` (UUID, human-readable prefix e.g. WM-2026-000123)
  - `organization` FK
  - `referring_user` FK (User, nullable for self-referral)
  - `referring_org` FK (Organization, nullable for cross-org referrals)
  - `form_data` (JSONField — field slug → value mapping)
  - `encrypted_pii` (TextField — Fernet-encrypted JSON of PII fields)
  - `status` FSM: `submitted → acknowledged → in_progress → resolved / rejected / withdrawn`
  - `delivery_channel` (chosen at submission from org's preferences)
  - `consent_given` BooleanField + `consent_timestamp`
  - `priority` (normal/urgent/emergency)
  - `notes` TextField (volunteer's notes, not shown to client)
  - `created_at`, `updated_at`
- [ ] Field-level encryption: PII fields encrypted with org-specific key (or platform master key)
- [ ] `ReferralStatusHistory` model: referral FK, from_status, to_status, changed_by, changed_at, note
- [ ] Self-referral flow: public user fills own referral form → submitted without volunteer
- [ ] Tests

#### M4.3 — Multi-Channel Delivery (No-Loss)
- [ ] `ReferralDelivery` model: referral FK, channel, status (queued/sent/failed/acknowledged), attempts, last_attempted_at, error_log
- [ ] **In-platform inbox** (always stored — no delivery failure possible): org_manager sees referrals in portal
- [ ] **Email delivery**: Celery task sends formatted referral email to org contact_email; HTML + plain text; attachment optional; max 3 retries with exponential backoff
- [ ] **CSV batch download**: org manager portal — download all referrals in date range as CSV (PII decrypted for authorised user only)
- [ ] **Print/Paper view**: `/portal/referrals/<ref>/print/` — printer-friendly layout, no nav, suitable for physical filing
- [ ] **CRM webhook**: org configures webhook URL + secret; Celery posts JSON payload on each new referral; HMAC-signed; retried on failure; logs each attempt
- [ ] **Channel fallback**: if preferred channel fails after max retries → escalate to admin alert + flag referral as `delivery_failed`
- [ ] Tests

#### M4.4 — Acknowledgment & Escalation
- [ ] Org managers must explicitly acknowledge receipt of each referral (one-click in portal/email)
- [ ] `acknowledged_at` + `acknowledged_by` on Referral
- [ ] Celery beat: 24h check — unacknowledged referrals → reminder email to org
- [ ] 48h check — still unacknowledged → alert to platform admin + flag `escalated`
- [ ] Referral SLA dashboard (admin only): by-org acknowledgment stats, average time-to-ack, failure rates
- [ ] Tests

#### M4.5 — Audit Chain
- [ ] `AuditEntry` model: hash-chained (SHA-256 of prev_hash + current record), actor, action, target_ct/pk, delta JSON, timestamp
- [ ] Every referral status change, delivery attempt, and PII access logged
- [ ] Admin audit viewer: filterable by actor/org/date/action
- [ ] Export audit log as CSV (admin only)
- [ ] Tests

#### M4.6 — Notifications & Newsfeed
- [ ] Email notifications: referral received (org), referral status updated (referring user), user account approved (admin→user)
- [ ] Notification model: user FK, type, read_at, link, created_at
- [ ] In-platform notification bell (HTMX polling or Server-Sent Events)
- [ ] Newsfeed: `NewsItem` model — title, body, source_url, published_at, org FK (optional), is_published
- [ ] Manual news creation in admin
- [ ] Scraped news from org news_page_url (BeautifulSoup, same pattern as event scraper)
- [ ] Public newsfeed page with pagination
- [ ] Tests + gate

---

## Phase 5 — Pathways ⬜

### Goal
Dedicated, curated portal sections for two high-need population groups.

### Milestones
- [ ] Prison leavers pathway: curated org list, "first week" checklist, step-by-step guidance content
- [ ] Homelessness pathway: emergency contacts, curated services, entitlements explainer
- [ ] Content managed via Django admin (simple Page/Section models)
- [ ] Linked to AI assistant (Phase 6) for dynamic questions
- [ ] Tests + gate

---

## Phase 6 — AI Assistant ⬜

### Goal
A chat-based assistant that helps any user navigate services, powered by semantic search over all platform content.

### Milestones
- [ ] pgvector extension enabled in prod DB
- [ ] Indexing pipeline: sentence-transformers embeds org/service/event/news content → pgvector
- [ ] Obsidian file watcher: syncs vault Markdown to vector store
- [ ] Chat UI: HTMX streaming response display
- [ ] Gemini 2.5 Flash: RAG pipeline — retrieve top-k, build context, generate response
- [ ] Conversation history per session (Django session or DB)
- [ ] Rate limiting per user
- [ ] Tests + gate
