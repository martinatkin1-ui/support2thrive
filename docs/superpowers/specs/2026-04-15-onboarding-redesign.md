# Onboarding Redesign — Design Spec
**Date:** 2026-04-15
**Status:** Approved
**Scope:** Redesign the 5-step organisation onboarding wizard with scrape-first UX, visual service picker, drag-and-drop referral form builder (with dual form support), and Gemini-powered website population.

---

## 1. Architecture

### What changes
The existing 5-step wizard (`apps/organizations/onboarding_views.py`, `apps/organizations/forms.py`, `templates/portal/onboarding/`) is redesigned in place. No new Django apps. Step names and `OrgOnboardingState.STEPS` keys remain the same (`about`, `services`, `referral_config`, `scraping`, `review`).

### New files
| File | Purpose |
|---|---|
| `apps/organizations/scraping.py` | `scrape_org_website(url) -> dict` — fetches page, calls Gemini, returns structured JSON |
| `apps/core/gemini_client.py` | Shared Gemini 2.5 Flash client (used by onboarding + Phase 6 RAG) |

### Model changes
- `ReferralFormField` gains a `form_type` field: `CharField(choices=[('self','Self-referral'),('professional','Organisation referral'),('both','Both forms')], default='both')` — allows fields to belong to one or both forms
- `Organization` gains `self_referral_channels` (JSONField, replaces `referral_delivery_channels`), `professional_referral_channels` (JSONField), `self_referral_email` (EmailField, replaces `referral_email`), `professional_referral_email` (EmailField). CRM webhook URL + secret remain shared across both forms. A data migration copies existing `referral_delivery_channels` → `self_referral_channels` and `referral_email` → `self_referral_email`.

### Gemini integration
`apps/core/gemini_client.py` wraps `google-generativeai`. The onboarding scraper sends page HTML + a structured extraction prompt, receives JSON:
```json
{
  "name": "...",
  "short_description": "...",
  "description": "...",
  "phone": "...",
  "email": "...",
  "address_line_1": "...",
  "city": "...",
  "postcode": "...",
  "services": ["Mental Health", "Counselling", "Crisis Support"],
  "events": [{"title": "...", "date": "...", "description": "..."}],
  "events_page_url": "...",
  "news_page_url": "..."
}
```
Services are matched against `ServiceCategory` slugs/names to produce `suggested_category_ids`. Events are saved as `Event` drafts (`is_published=False, is_scraped=True`). The same Gemini client is imported by Phase 6's RAG pipeline — built once, shared.

**RAG brain population:** `scrape_org_website()` also returns `raw_text` (the full cleaned page text). This is saved as an `OrgDocument` record (`source_type='website_scrape'`) on the org at scrape time. Phase 6's `index_org_document` Celery task fires via post_save signal and embeds this text into pgvector — meaning the AI assistant immediately knows everything on the org's public website, not just the structured fields. The weekly scrape task (`scrape_org_events`) is extended to also refresh this `OrgDocument` with updated page text, keeping the AI brain current.

### HTMX scrape endpoint
New view: `POST /portal/onboarding/scrape/` → calls `scrape_org_website(url)` → returns JSON response. Step 1 form uses HTMX to POST the URL and populate fields from the JSON response without a page reload. 5–10 second operation — response includes a spinner state.

---

## 2. Step 1 — Smart Import *(replaces "About")*

**Goal:** Pre-fill the org profile from their website with one click.

**UI flow:**
1. URL input bar + "⚡ Populate from website" button (blue, prominent)
2. On click: HTMX POST → spinner state ("Scanning your website with AI…")
3. On success: green banner ("AI scan complete — review and edit anything below") + amber "Imported" badge on each pre-filled field
4. All fields remain fully editable after import
5. "Also found:" amber pill row shows counts: "3 services to confirm on next step" + "2 events saved as drafts"

**Fields:**
- Organisation name, short description (300 chars), full description (textarea)
- Phone, email, website URL
- Address line 1, city, postcode
- Logo upload (drag & drop or file picker — not scraped, always manual)

**Fallback:** "No website? Fill in manually →" link skips scraping and shows blank form.

**On save:** Org fields written, `OrgOnboardingState.mark_step_complete("about")`. Scraped events already saved as drafts at scrape time (not at save time).

---

## 3. Step 2 — Services *(redesigned)*

**Goal:** Fast, visual service selection with AI pre-selection.

**Service picker:**
- Full-width searchable chip grid of all active `ServiceCategory` records
- Chips matched from Gemini's scrape highlighted amber with ⭐ prefix, pre-selected
- Click chip → selected (blue filled); click again → deselected
- Search input filters chips in real time (JS, no reload)

**Service detail (per selected chip):**
- Collapsible detail card below the grid, one per selected category
- Fields: service name (editable, defaults to category name), access model dropdown (drop-in / self-referral / professional_referral / gp_referral / assessment), age range (min/max), eligibility notes — all optional
- "+ Add another service" button creates a blank detail card for an uncategorised service

**Geographic coverage:**
- Separate chip section below: `GeographicArea` names as chips
- Same select/deselect pattern

**Support streams:**
- Auto-derived from selected `ServiceCategory.support_stream` FK values
- Shown as read-only confirmation badges ("Covers: Mental Health · Crisis · Housing") — not a separate picker

**On save:** `OrganizationService` records created/updated, `areas_served` M2M written, `mark_step_complete("services")`.

---

## 4. Step 3 — Referral Setup *(redesigned)*

### 4a. Dual form tabs
Top of step: two tabs — **"Self-referral"** and **"Organisation referral"**. Each tab has:
- Its own independent delivery channel config (using the new per-form channel fields on `Organization`)
- Its own drag-and-drop form canvas
- `ReferralFormField.form_type` distinguishes which form a field belongs to (`self`, `professional`, or `both`)
- Fields with `form_type='both'` appear on both canvases — editing one syncs to the other

### 4b. Delivery channels
Card grid — one card per channel:
| Channel | Always on | Expandable config |
|---|---|---|
| Platform inbox | ✓ locked | — |
| Email | toggle | `referral_email` input |
| CSV export | toggle | — |
| Print PDF | toggle | — |
| CRM Webhook | toggle | webhook URL + secret inputs |

Toggle switches (not checkboxes). Config fields expand inline when toggled on.

### 4c. Form builder
**Palette** (field type chips):
- Name, Email, Phone, Date of Birth, NHS Number, NI Number, DBS Number, Free text, Yes/No, File upload, Dropdown (with options), Consent checkbox

**Canvas:**
- Drag from palette → dropped field appears as a card on the canvas
- Reorder by dragging (Sortable.js)
- Each canvas field card shows:
  - ⠿ drag handle
  - Editable label (click to rename — e.g. "Text" → "Client ID Number")
  - Field type badge
  - Required / Optional toggle
  - ✏️ edit popover: label, help text, placeholder, options (for dropdowns)
  - 🗑 delete button

**GDPR consent:** Always pinned at bottom of canvas, cannot be deleted or reordered above other fields. Shown with a lock icon.

**On save:** `ReferralFormField` records written with `form_type` set per active tab, `mark_step_complete("referral_config")`.

---

## 5. Step 4 — Website Config *(light redesign)*

**Goal:** Confirm which pages to scrape weekly for events and news.

- Events page URL input — pre-filled from Step 1 scrape if detected
- News page URL input — pre-filled from Step 1 scrape if detected
- Info banner: "We scan these pages weekly to keep your events and news up to date"
- Skip link: "Set this up later" (marks step complete without saving URLs)

**On save:** `org.events_page_url`, `org.news_page_url` written, `mark_step_complete("scraping")`.

---

## 6. Step 5 — Review & Publish *(redesigned)*

**Goal:** Confidence before going live.

- One summary card per completed step with an "Edit" pencil link returning to that step
- Completeness nudge: list of optional fields not yet filled (e.g. "Consider adding a hero image")
- Large amber "Publish your organisation" CTA — only shown if all required steps complete
- On publish: `org.status = "active"`, `AuditEntry` logged, redirect to portal dashboard with success toast "Your organisation is now live 🎉"

---

## 7. Design System Compliance

All templates use the existing design tokens from `design-system/MASTER.md`:
- Primary button: `bg-blue-800 hover:bg-blue-900 focus:ring-amber-500`
- CTA button (Publish): `bg-amber-500 hover:bg-amber-600`
- Cards: `rounded-xl bg-white shadow-sm border border-slate-200`
- Fonts: Fraunces for wizard title, Figtree for UI, Noto Sans for form inputs
- Amber "Imported" badges: `bg-yellow-100 text-yellow-800`
- Touch targets: `min-h-[44px]` on all interactive elements
- RTL: `ms-`/`me-` margin utilities throughout

Sortable.js loaded via CDN `<script>` tag in `templates/portal/onboarding/base_wizard.html` — no npm build step needed.

---

## 8. What's Not Changing

- `OrgOnboardingState` model and step keys — unchanged
- `OnboardingRedirectMiddleware` — unchanged
- `ReferralFormField` field types — unchanged (all 15 types retained)
- All existing tests — extended, not replaced
- Scraping step URL (`/portal/onboarding/scraping/`) — unchanged

---

## 9. Verification

1. Start dev server: `python manage.py runserver`
2. Register a new org manager account
3. Navigate to portal — middleware redirects to `/portal/onboarding/about/`
4. Enter a real website URL → click "Populate from website" → confirm fields pre-fill within 10 seconds
5. Proceed through all 5 steps → confirm publish sets `org.status = "active"`
6. Check Events dashboard — confirm scraped events appear as unpublished drafts
7. Submit a self-referral to the org — confirm only "self" form fields appear
8. Submit a professional referral — confirm "professional" form fields appear
9. Run: `python manage.py test apps.organizations apps.referrals --settings=config.settings.test`
10. Run: `ruff check apps/ -q`
