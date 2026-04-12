# WMCSP — Requirements

## Functional Requirements

### FR-1: Organisation Directory (Phase 1 — DONE)
- Public can browse all active organisations without login
- Filter by support stream and geographic area
- Each organisation has a detail page: description, services, contact, opening hours
- REST API endpoint for organisation list and detail
- Organisation model supports: logo, hero image, geo-coordinates, referral config, translated descriptions, scraping URLs, RAG indexing timestamp

### FR-2: User Accounts & Roles (Phase 1 — DONE)
- Self-registration with role selection: public / volunteer / org_manager
- Public users auto-approved; volunteers and org_managers require admin approval
- Login / logout / profile
- User carries: role, phone, preferred language, linked organisation, approval status
- Business rules: only approved volunteers/managers/admins can create referrals

### FR-3: Events & Calendar (Phase 2 — NEXT)
- Organisations can create, edit, and delete events
- Events have: title, description, location, start/end datetime, image, capacity, booking URL
- Recurrence rules (weekly, monthly) with individual occurrence overrides
- Public calendar view with filtering by date, stream, area
- HTMX-powered date navigation (no full page reload)
- iCal export per organisation and per stream
- Scraper harvests events from `events_page_url` weekly via Celery

### FR-4: Service Category Taxonomy (Phase 3)
- Hierarchical service categories (parent → child, e.g. "Mental Health" → "Crisis Support")
- Each OrganizationService links to a category node
- Public can browse services by category tree
- Admin can manage the taxonomy

### FR-5: Secure Referral System (Phase 4)
- Volunteers and org_managers can create referrals to any active organisation
- Referral stores: client name, DOB, contact, presenting need, urgency, consent confirmation
- All PII fields encrypted at rest (field-level encryption)
- Receiving organisation is notified by email when a referral arrives
- Referral statuses: pending → acknowledged → accepted / declined / completed
- Referral creator can view status of their own referrals only
- Audit log entry on every status change

### FR-6: Hash-Chained Audit Log (Phase 4)
- Every significant action (referral created/changed, user approved, org updated) creates an AuditEntry
- Each entry stores: actor, action, target object, timestamp, delta JSON, previous hash, current hash
- Chain is verifiable — tampering with any entry breaks subsequent hashes
- Admin-only read access; no delete

### FR-7: Email & SMS Notifications (Phase 4)
- Email notification on: referral received, referral status change, account approved/rejected
- SMS notification (optional, Twilio): urgent referral received
- Celery handles all sending asynchronously
- Notification preferences per user

### FR-8: Newsfeed (Phase 4b)
- Manual news items created by org_managers (title, body, image, link, published_at)
- Auto-scraped news from `news_page_url` via Celery weekly
- Public newsfeed page, filterable by organisation and stream

### FR-9: Prison Leavers & Homelessness Pathways (Phase 5)
- Dedicated portal sections for two high-need groups
- Curated service lists specific to each pathway (resettlement, housing)
- Step-by-step guidance ("First week out of prison" checklist)
- Integrated with AI assistant (Phase 6)

### FR-10: RAG AI Assistant (Phase 6)
- Chat interface available to all public users
- Backed by pgvector semantic search over organisations, services, events, news
- Gemini 2.5 Flash generates responses grounded in retrieved context
- Conversation history retained per session
- Obsidian vault files can be indexed as additional knowledge base content
- File watcher syncs Obsidian changes to the vector store

## Non-Functional Requirements

| # | Requirement | Target |
|---|---|---|
| NFR-1 | Mobile-first responsive UI | All views usable on 375px width |
| NFR-2 | i18n | 10 languages; RTL for Arabic & Urdu |
| NFR-3 | PII encryption | Referral PII encrypted at rest |
| NFR-4 | GDPR compliance | Data retention policies, right to erasure, consent logging |
| NFR-5 | Audit trail | Tamper-evident hash chain on all sensitive actions |
| NFR-6 | Performance | List views load < 2s on 4G; N+1 queries prevented |
| NFR-7 | Accessibility | WCAG 2.1 AA minimum |
| NFR-8 | Test coverage | ≥ 80% coverage on all apps |
| NFR-9 | Security | OWASP Top 10 addressed; django-axes brute-force protection |
| NFR-10 | Deployment | Docker-compose for prod; gunicorn + PostgreSQL |
