# Onboarding Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the raw-formset onboarding wizard with a scrape-first, visually polished 5-step flow — Gemini reads the org's website and pre-populates name, description, services, and events; a chip-based service picker replaces checkboxes; a drag-and-drop canvas replaces the referral field formset; dual self/professional referral forms are introduced.

**Architecture:** A shared `apps/core/gemini_client.py` wraps `google.generativeai` and is imported by both the onboarding scraper and the Phase 6 RAG pipeline. `apps/organizations/scraping.py` fetches a URL, sends the HTML to Gemini 2.5 Flash, and returns a structured dict. All five onboarding views and templates are replaced in-place — no new apps, no step key changes. Two new model migrations add `form_type` to `ReferralFormField` and dual channel fields to `Organization`. Sortable.js (CDN) powers the drag-and-drop form builder.

**Tech Stack:** Django 6.0.x · HTMX · Tailwind CSS · `google-generativeai` · `beautifulsoup4` (already installed) · Sortable.js 1.15 (CDN) · Django TestCase

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `apps/core/gemini_client.py` | Shared Gemini 2.5 Flash client |
| Create | `apps/organizations/scraping.py` | `scrape_org_website(url)` → structured dict |
| Modify | `requirements.txt` | Add `google-generativeai` |
| Modify | `apps/organizations/models.py` | Add dual referral channel fields |
| Create | `apps/organizations/migrations/0006_…` | Data migration for new channel fields |
| Modify | `apps/referrals/models.py` | Add `form_type` to `ReferralFormField` |
| Create | `apps/referrals/migrations/0003_…` | Migration for `form_type` |
| Modify | `apps/organizations/onboarding_views.py` | All 5 step views + new scrape endpoint |
| Modify | `apps/organizations/forms.py` | Slim forms for new step designs |
| Modify | `apps/organizations/urls.py` | Add `/onboarding/scrape/` URL |
| Modify | `templates/portal/onboarding/base_wizard.html` | Sortable.js CDN + step labels |
| Replace | `templates/portal/onboarding/step_about.html` | Smart Import UI |
| Replace | `templates/portal/onboarding/step_services.html` | Chip picker |
| Replace | `templates/portal/onboarding/step_referral_config.html` | Drag-drop dual-tab builder |
| Replace | `templates/portal/onboarding/step_scraping.html` | Pre-filled URL config |
| Replace | `templates/portal/onboarding/step_review.html` | Card summary + publish |
| Modify | `apps/organizations/tests.py` | Tests for all new behaviour |
| Modify | `apps/referrals/tests.py` | Tests for form_type |

---

## Task 1: Add `google-generativeai` and create shared Gemini client

**Files:**
- Modify: `requirements.txt`
- Create: `apps/core/gemini_client.py`
- Modify: `apps/core/tests.py` (add smoke test)

- [ ] **Step 1: Add package to requirements.txt**

  Open `requirements.txt` and add after `google` or alphabetically:

  ```
  google-generativeai==0.8.5
  ```

- [ ] **Step 2: Install it**

  ```bash
  pip install google-generativeai==0.8.5
  ```

  Expected: Successfully installed google-generativeai and its deps (grpcio, googleapis-common-protos, etc.)

- [ ] **Step 3: Write the failing test**

  In `apps/core/tests.py`, add at the bottom:

  ```python
  from unittest.mock import MagicMock, patch

  class GeminiClientTest(TestCase):
      @patch("apps.core.gemini_client.genai")
      def test_generate_returns_text(self, mock_genai):
          mock_model = MagicMock()
          mock_model.generate_content.return_value.text = "hello"
          mock_genai.GenerativeModel.return_value = mock_model

          from apps.core.gemini_client import generate_text
          result = generate_text("say hello")
          self.assertEqual(result, "hello")
  ```

- [ ] **Step 4: Run test — confirm it fails**

  ```bash
  python manage.py test apps.core.tests.GeminiClientTest --settings=config.settings.test
  ```

  Expected: `ModuleNotFoundError: No module named 'apps.core.gemini_client'`

- [ ] **Step 5: Create `apps/core/gemini_client.py`**

  ```python
  """
  Shared Gemini 2.5 Flash client.

  Used by:
  - apps.organizations.scraping  (onboarding website scraper)
  - apps.assistant.rag_service   (Phase 6 RAG pipeline)

  Usage:
      from apps.core.gemini_client import generate_text
      text = generate_text("your prompt here")
  """
  import google.generativeai as genai
  from django.conf import settings

  _model = None


  def _get_model():
      global _model
      if _model is None:
          genai.configure(api_key=settings.GEMINI_API_KEY)
          _model = genai.GenerativeModel(
              getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash-preview-04-17")
          )
      return _model


  def generate_text(prompt: str) -> str:
      """Send a prompt to Gemini and return the response text."""
      model = _get_model()
      response = model.generate_content(prompt)
      return response.text
  ```

- [ ] **Step 6: Run test — confirm it passes**

  ```bash
  python manage.py test apps.core.tests.GeminiClientTest --settings=config.settings.test
  ```

  Expected: `OK`

- [ ] **Step 7: Add `GEMINI_MODEL` to `.env.example`**

  Add line:
  ```
  GEMINI_MODEL=gemini-2.5-flash-preview-04-17
  ```

- [ ] **Step 8: Commit**

  ```bash
  git add requirements.txt apps/core/gemini_client.py apps/core/tests.py .env.example
  git commit -m "feat: shared Gemini 2.5 Flash client in apps/core"
  ```

---

## Task 2: Model migrations — dual referral channels + form_type

**Files:**
- Modify: `apps/organizations/models.py`
- Create: `apps/organizations/migrations/0006_organization_dual_referral_channels.py`
- Modify: `apps/referrals/models.py`
- Create: `apps/referrals/migrations/0003_referralformfield_form_type.py`

- [ ] **Step 1: Write failing tests for new fields**

  In `apps/organizations/tests.py`, add to `OrganizationModelTest`:

  ```python
  def test_dual_referral_channel_fields_exist(self):
      org = Organization.objects.create(
          name="Chan Test",
          short_description="x",
          description="y",
      )
      # New fields default to empty list / empty string
      self.assertEqual(org.self_referral_channels, [])
      self.assertEqual(org.professional_referral_channels, [])
      self.assertEqual(org.self_referral_email, "")
      self.assertEqual(org.professional_referral_email, "")
  ```

  In `apps/referrals/tests.py`, add:

  ```python
  from apps.referrals.models import ReferralFormField
  from apps.organizations.models import Organization

  class ReferralFormFieldFormTypeTest(TestCase):
      def test_form_type_defaults_to_both(self):
          org = Organization.objects.create(
              name="FT Org", short_description="x", description="y"
          )
          field = ReferralFormField.objects.create(
              organization=org,
              field_type="text",
              label="Name",
              display_order=1,
          )
          self.assertEqual(field.form_type, "both")

      def test_form_type_accepts_self_and_professional(self):
          org = Organization.objects.create(
              name="FT Org2", short_description="x", description="y"
          )
          for ft in ("self", "professional", "both"):
              f = ReferralFormField(
                  organization=org, field_type="text",
                  label=f"Label {ft}", display_order=1, form_type=ft
              )
              f.full_clean()  # should not raise
  ```

- [ ] **Step 2: Run tests — confirm they fail**

  ```bash
  python manage.py test apps.organizations.tests.OrganizationModelTest.test_dual_referral_channel_fields_exist apps.referrals.tests.ReferralFormFieldFormTypeTest --settings=config.settings.test
  ```

  Expected: `FieldError` or `AttributeError` — fields don't exist yet.

- [ ] **Step 3: Add new fields to `apps/organizations/models.py`**

  Find the existing referral fields block (around line 83) and add after `referral_delivery_channels`:

  ```python
  # Dual referral form channels (self-referral vs professional referral)
  self_referral_channels = models.JSONField(
      _("self-referral delivery channels"),
      default=list,
      help_text=_("Channels for self-referral form. Replaces referral_delivery_channels for self-referral."),
  )
  professional_referral_channels = models.JSONField(
      _("professional referral delivery channels"),
      default=list,
  )
  self_referral_email = models.EmailField(
      _("self-referral email"),
      blank=True,
      default="",
  )
  professional_referral_email = models.EmailField(
      _("professional referral email"),
      blank=True,
      default="",
  )
  ```

  Also update `completion_score` property — find where `"referral_email": 10` is set and add:

  ```python
  "self_referral_email": 5,
  "professional_referral_email": 5,
  ```

- [ ] **Step 4: Add `form_type` to `apps/referrals/models.py`**

  Find the `ReferralFormField` class and add after `is_active`:

  ```python
  FORM_TYPE_CHOICES = [
      ("self", _("Self-referral form")),
      ("professional", _("Organisation referral form")),
      ("both", _("Both forms")),
  ]
  form_type = models.CharField(
      _("form type"),
      max_length=16,
      choices=FORM_TYPE_CHOICES,
      default="both",
  )
  ```

- [ ] **Step 5: Make and apply migrations**

  ```bash
  python manage.py makemigrations organizations --name="dual_referral_channels"
  python manage.py makemigrations referrals --name="referralformfield_form_type"
  python manage.py migrate --settings=config.settings.test
  ```

  Expected: two new migration files created, migrations applied.

- [ ] **Step 6: Run tests — confirm they pass**

  ```bash
  python manage.py test apps.organizations.tests.OrganizationModelTest.test_dual_referral_channel_fields_exist apps.referrals.tests.ReferralFormFieldFormTypeTest --settings=config.settings.test
  ```

  Expected: `OK`

- [ ] **Step 7: Commit**

  ```bash
  git add apps/organizations/models.py apps/organizations/migrations/ apps/referrals/models.py apps/referrals/migrations/
  git commit -m "feat: dual referral channel fields + ReferralFormField.form_type"
  ```

---

## Task 3: Scraping service

**Files:**
- Create: `apps/organizations/scraping.py`
- Modify: `apps/organizations/tests.py`

- [ ] **Step 1: Write failing tests**

  In `apps/organizations/tests.py`, add:

  ```python
  from unittest.mock import MagicMock, patch

  class ScrapingServiceTest(TestCase):
      @patch("apps.organizations.scraping.requests.get")
      @patch("apps.organizations.scraping.generate_text")
      def test_scrape_returns_structured_dict(self, mock_gemini, mock_get):
          mock_get.return_value.text = "<html><body>Wolverhampton Mind</body></html>"
          mock_get.return_value.status_code = 200
          mock_gemini.return_value = '''{
              "name": "Wolverhampton Mind",
              "short_description": "Mental health support",
              "description": "Full desc",
              "phone": "01902 123456",
              "email": "info@example.org",
              "address_line_1": "1 High Street",
              "city": "Wolverhampton",
              "postcode": "WV1 1AA",
              "services": ["Mental Health", "Counselling"],
              "events": [],
              "events_page_url": "",
              "news_page_url": "",
              "raw_text": "Wolverhampton Mind mental health support"
          }'''

          from apps.organizations.scraping import scrape_org_website
          result = scrape_org_website("https://example.org")

          self.assertEqual(result["name"], "Wolverhampton Mind")
          self.assertIn("Mental Health", result["services"])
          self.assertIn("raw_text", result)

      @patch("apps.organizations.scraping.requests.get")
      def test_scrape_handles_request_failure(self, mock_get):
          import requests
          mock_get.side_effect = requests.RequestException("timeout")

          from apps.organizations.scraping import scrape_org_website
          result = scrape_org_website("https://bad-url.invalid")

          self.assertIsNone(result)
  ```

- [ ] **Step 2: Run tests — confirm they fail**

  ```bash
  python manage.py test apps.organizations.tests.ScrapingServiceTest --settings=config.settings.test
  ```

  Expected: `ModuleNotFoundError: No module named 'apps.organizations.scraping'`

- [ ] **Step 3: Create `apps/organizations/scraping.py`**

  ```python
  """
  Gemini-powered website scraper for org onboarding.

  scrape_org_website(url) -> dict | None

  Returns a dict with structured org info extracted by Gemini 2.5 Flash,
  or None if the page cannot be fetched or parsed.

  The returned dict always contains:
    name, short_description, description, phone, email,
    address_line_1, city, postcode,
    services (list of str), events (list of {title, date, description}),
    events_page_url, news_page_url,
    raw_text (full cleaned page text for RAG indexing)
  """
  import json
  import logging

  import requests
  from bs4 import BeautifulSoup

  from apps.core.gemini_client import generate_text

  logger = logging.getLogger(__name__)

  _EXTRACTION_PROMPT = """
  You are extracting structured information from an organisation's website for a community directory.

  Return ONLY valid JSON matching this exact schema — no markdown, no explanation:
  {{
    "name": "Organisation name or empty string",
    "short_description": "One sentence summary, max 300 chars, or empty string",
    "description": "2-3 paragraph description of what the org does, or empty string",
    "phone": "Phone number or empty string",
    "email": "Contact email or empty string",
    "address_line_1": "Street address or empty string",
    "city": "City or empty string",
    "postcode": "UK postcode or empty string",
    "services": ["List of service names this org provides"],
    "events": [{{"title": "Event title", "date": "YYYY-MM-DD or empty", "description": "Brief desc or empty"}}],
    "events_page_url": "URL of events/what's on page, or empty string",
    "news_page_url": "URL of news/blog page, or empty string"
  }}

  Website content:
  {content}
  """


  def scrape_org_website(url: str) -> dict | None:
      """
      Fetch url, extract text, send to Gemini, return structured dict.
      Returns None on any network or parse failure.
      """
      try:
          response = requests.get(url, timeout=15, headers={"User-Agent": "Support2Thrive/1.0"})
          response.raise_for_status()
      except requests.RequestException as exc:
          logger.warning("scrape_org_website: fetch failed for %s: %s", url, exc)
          return None

      soup = BeautifulSoup(response.text, "html.parser")

      # Remove nav, footer, scripts, styles — keep content
      for tag in soup(["script", "style", "nav", "footer", "header"]):
          tag.decompose()

      raw_text = soup.get_text(separator=" ", strip=True)
      # Truncate to ~8000 chars to stay within Gemini context
      content_for_gemini = raw_text[:8000]

      prompt = _EXTRACTION_PROMPT.format(content=content_for_gemini)

      try:
          gemini_response = generate_text(prompt)
          # Strip markdown code fences if Gemini adds them
          cleaned = gemini_response.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
          data = json.loads(cleaned)
      except (ValueError, KeyError) as exc:
          logger.warning("scrape_org_website: Gemini parse failed for %s: %s", url, exc)
          return None

      # Inject raw_text for RAG indexing
      data["raw_text"] = raw_text[:20000]
      return data
  ```

- [ ] **Step 4: Run tests — confirm they pass**

  ```bash
  python manage.py test apps.organizations.tests.ScrapingServiceTest --settings=config.settings.test
  ```

  Expected: `OK`

- [ ] **Step 5: Commit**

  ```bash
  git add apps/organizations/scraping.py apps/organizations/tests.py
  git commit -m "feat: Gemini-powered website scraping service"
  ```

---

## Task 4: HTMX scrape endpoint

**Files:**
- Modify: `apps/organizations/onboarding_views.py`
- Modify: `apps/organizations/urls.py`
- Modify: `apps/organizations/tests.py`

- [ ] **Step 1: Write failing test**

  In `apps/organizations/tests.py`, add:

  ```python
  from unittest.mock import patch
  import json

  class OnboardingScrapeEndpointTest(TestCase):
      def setUp(self):
          self.org = _onboarding_org()
          self.user = _org_manager(self.org)
          self.client.login(username="testmanager", password="testpass")

      @patch("apps.organizations.onboarding_views.scrape_org_website")
      def test_scrape_endpoint_returns_json(self, mock_scrape):
          mock_scrape.return_value = {
              "name": "Test Org",
              "short_description": "A test",
              "description": "Full desc",
              "phone": "01902 111111",
              "email": "test@test.org",
              "address_line_1": "1 Test St",
              "city": "Wolverhampton",
              "postcode": "WV1 1AA",
              "services": ["Mental Health"],
              "events": [],
              "events_page_url": "",
              "news_page_url": "",
              "raw_text": "Test org content",
          }
          resp = self.client.post(
              "/portal/onboarding/scrape/",
              data={"url": "https://test.org"},
              HTTP_HX_REQUEST="true",
          )
          self.assertEqual(resp.status_code, 200)
          data = json.loads(resp.content)
          self.assertEqual(data["name"], "Test Org")
          self.assertIn("suggested_category_ids", data)

      @patch("apps.organizations.onboarding_views.scrape_org_website")
      def test_scrape_endpoint_returns_error_on_failure(self, mock_scrape):
          mock_scrape.return_value = None
          resp = self.client.post(
              "/portal/onboarding/scrape/",
              data={"url": "https://bad.invalid"},
              HTTP_HX_REQUEST="true",
          )
          self.assertEqual(resp.status_code, 200)
          data = json.loads(resp.content)
          self.assertIn("error", data)
  ```

- [ ] **Step 2: Run test — confirm it fails**

  ```bash
  python manage.py test apps.organizations.tests.OnboardingScrapeEndpointTest --settings=config.settings.test
  ```

  Expected: `404` — URL not yet registered.

- [ ] **Step 3: Add scrape view to `apps/organizations/onboarding_views.py`**

  Add these imports at the top:
  ```python
  import json
  from django.http import JsonResponse
  from apps.services.models import ServiceCategory
  from .scraping import scrape_org_website
  ```

  Add view function before `onboarding_wizard`:

  ```python
  @login_required
  def onboarding_scrape_view(request):
      """
      HTMX endpoint: POST {'url': '...'} → JSON with pre-filled org fields
      and suggested_category_ids matched from Gemini's services list.
      """
      if request.method != "POST":
          return JsonResponse({"error": "POST required"}, status=405)

      url = request.POST.get("url", "").strip()
      if not url:
          return JsonResponse({"error": "URL is required"})

      result = scrape_org_website(url)
      if result is None:
          return JsonResponse({
              "error": "Could not read that website. Please check the URL or fill in manually."
          })

      # Match scraped service names against ServiceCategory records
      scraped_services = result.get("services", [])
      all_categories = ServiceCategory.objects.filter(is_active=True).values("id", "name", "slug")
      suggested_ids = []
      for category in all_categories:
          cat_name_lower = category["name"].lower()
          if any(cat_name_lower in s.lower() or s.lower() in cat_name_lower
                 for s in scraped_services):
              suggested_ids.append(category["id"])

      # Store raw_text in session for OrgDocument creation on save
      request.session["scrape_raw_text"] = result.get("raw_text", "")
      request.session["scrape_url"] = url

      return JsonResponse({
          "name": result.get("name", ""),
          "short_description": result.get("short_description", ""),
          "description": result.get("description", ""),
          "phone": result.get("phone", ""),
          "email": result.get("email", ""),
          "address_line_1": result.get("address_line_1", ""),
          "city": result.get("city", ""),
          "postcode": result.get("postcode", ""),
          "events_page_url": result.get("events_page_url", ""),
          "news_page_url": result.get("news_page_url", ""),
          "suggested_category_ids": suggested_ids,
          "scraped_services": scraped_services,
          "events_found": len(result.get("events", [])),
      })
  ```

- [ ] **Step 4: Register URL in `apps/organizations/urls.py`**

  The org URLs are registered in `apps/organizations/urls.py` under the `organizations` namespace. Add after the existing onboarding paths:

  ```python
  from .onboarding_views import onboarding_scrape_view

  # Inside urlpatterns (after existing onboarding_step path):
  path("portal/onboarding/scrape/", onboarding_scrape_view, name="onboarding_scrape"),
  ```

  The named URL will be `organizations:onboarding_scrape`. Update the HTMX button in `step_about.html` to use `{% url 'organizations:onboarding_scrape' %}`.

- [ ] **Step 5: Run tests — confirm they pass**

  ```bash
  python manage.py test apps.organizations.tests.OnboardingScrapeEndpointTest --settings=config.settings.test
  ```

  Expected: `OK`

- [ ] **Step 6: Commit**

  ```bash
  git add apps/organizations/onboarding_views.py apps/organizations/urls.py apps/organizations/tests.py
  git commit -m "feat: HTMX scrape endpoint /portal/onboarding/scrape/"
  ```

---

## Task 5: Wizard base template — step labels + Sortable.js

**Files:**
- Modify: `templates/portal/onboarding/base_wizard.html`

- [ ] **Step 1: Update step labels and add Sortable.js**

  Replace the contents of `templates/portal/onboarding/base_wizard.html` with:

  ```html
  {% extends "base.html" %}
  {% load i18n %}

  {% block title %}{% trans "Set up your organisation" %}{% endblock %}

  {% block content %}
  <div class="min-h-screen bg-page py-8 px-4">
    <div class="max-w-3xl mx-auto">

      {{! Top bar }}
      <div class="mb-8">
        <h1 class="font-display text-2xl font-semibold text-slate-800">
          {% trans "Set up your organisation" %}
        </h1>
        <p class="text-sm text-slate-500 mt-1">{% trans "Step" %} {{ step_number }} {% trans "of" %} 5</p>
      </div>

      {{! Step progress track }}
      <div class="flex items-center mb-10" aria-label="{% trans 'Onboarding progress' %}">
        {% for label, slug in steps %}
        <div class="flex flex-col items-center flex-1">
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold
            {% if slug in completed_steps %}bg-blue-800 text-white
            {% elif slug == current_step %}bg-blue-800 text-white ring-4 ring-blue-200
            {% else %}bg-slate-100 text-slate-400 border-2 border-slate-200{% endif %}">
            {% if slug in completed_steps %}
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
            {% else %}
              {{ forloop.counter }}
            {% endif %}
          </div>
          <span class="text-xs mt-1 font-medium
            {% if slug == current_step %}text-blue-800
            {% elif slug in completed_steps %}text-green-600
            {% else %}text-slate-400{% endif %}">
            {{ label }}
          </span>
        </div>
        {% if not forloop.last %}
        <div class="flex-1 h-0.5 {% if slug in completed_steps %}bg-blue-800{% else %}bg-slate-200{% endif %} max-w-[60px] -mt-5"></div>
        {% endif %}
        {% endfor %}
      </div>

      {{! Step content }}
      <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        {% block step_content %}{% endblock %}

        {{! Navigation }}
        <div class="px-8 py-5 border-t border-slate-100 bg-slate-50 flex items-center justify-between">
          <div>
            {% if prev_step %}
            <a href="{% url 'onboarding_wizard' prev_step %}"
               class="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-slate-200 bg-white text-sm font-semibold text-slate-600 hover:bg-slate-50 min-h-[44px]">
              ← {% trans "Back" %}
            </a>
            {% endif %}
          </div>
          {% block nav_buttons %}
          <button type="submit" form="step-form"
                  class="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-blue-800 text-white text-sm font-bold hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 min-h-[44px]">
            {% trans "Save & continue" %} →
          </button>
          {% endblock %}
        </div>
      </div>

    </div>
  </div>
  {% endblock %}

  {% block extra_js %}
  <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.6/Sortable.min.js"></script>
  {% block wizard_js %}{% endblock %}
  {% endblock %}
  ```

- [ ] **Step 2: Update all 5 step views to pass `steps`, `step_number`, `completed_steps` context**

  In `apps/organizations/onboarding_views.py`, update the `_base_context()` helper (or add one if it doesn't exist):

  ```python
  STEP_LABELS = [
      ("Import", "about"),
      ("Services", "services"),
      ("Referrals", "referral_config"),
      ("Website", "scraping"),
      ("Publish", "review"),
  ]

  def _base_context(current_step, state, prev_step=None):
      return {
          "steps": STEP_LABELS,
          "current_step": current_step,
          "step_number": STEP_ORDER.index(current_step) + 1,
          "completed_steps": state.completed_steps,
          "prev_step": prev_step,
      }
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add templates/portal/onboarding/base_wizard.html apps/organizations/onboarding_views.py
  git commit -m "feat: wizard base template refresh — step labels, Sortable.js CDN"
  ```

---

## Task 6: Step 1 — Smart Import

**Files:**
- Modify: `apps/organizations/onboarding_views.py` (`_step_about`)
- Modify: `apps/organizations/forms.py` (`OnboardingAboutForm`)
- Replace: `templates/portal/onboarding/step_about.html`
- Modify: `apps/organizations/tests.py`

- [ ] **Step 1: Write failing test**

  In `apps/organizations/tests.py`, add:

  ```python
  class StepAboutTest(TestCase):
      def setUp(self):
          self.org = _onboarding_org()
          self.user = _org_manager(self.org)
          self.client.login(username="testmanager", password="testpass")

      def test_step_about_get_renders(self):
          resp = self.client.get("/portal/onboarding/about/")
          self.assertEqual(resp.status_code, 200)
          self.assertContains(resp, "Populate from website")

      def test_step_about_post_saves_and_redirects(self):
          resp = self.client.post("/portal/onboarding/about/", {
              "name": "New Org Name",
              "short_description": "A short desc",
              "description": "A longer description of what we do",
              "website": "https://neworg.org",
              "email": "info@neworg.org",
              "phone": "01902 000000",
              "address_line_1": "1 Test Street",
              "city": "Wolverhampton",
              "postcode": "WV1 1AA",
          })
          self.assertRedirects(resp, "/portal/onboarding/services/")
          self.org.refresh_from_db()
          self.assertEqual(self.org.name, "New Org Name")

      def test_step_about_marks_step_complete(self):
          self.client.post("/portal/onboarding/about/", {
              "name": "New Org Name",
              "short_description": "A short desc",
              "description": "A longer description",
              "website": "https://neworg.org",
              "email": "info@neworg.org",
              "phone": "01902 000000",
              "address_line_1": "1 Test Street",
              "city": "Wolverhampton",
              "postcode": "WV1 1AA",
          })
          state = OrgOnboardingState.objects.get(organization=self.org)
          self.assertIn("about", state.completed_steps)
  ```

- [ ] **Step 2: Run tests — confirm they fail**

  ```bash
  python manage.py test apps.organizations.tests.StepAboutTest --settings=config.settings.test
  ```

  Expected: FAIL (template doesn't contain "Populate from website" yet)

- [ ] **Step 3: Replace `templates/portal/onboarding/step_about.html`**

  ```html
  {% extends "portal/onboarding/base_wizard.html" %}
  {% load i18n %}

  {% block step_content %}
  <div class="px-8 py-8">
    <h2 class="font-heading text-xl font-bold text-slate-800 mb-1">{% trans "Tell us about your organisation" %}</h2>
    <p class="text-sm text-slate-500 mb-6">{% trans "Enter your website and we'll fill this in for you — or type it manually." %}</p>

    {{! Scrape bar }}
    <div class="mb-6">
      <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1.5" for="id_scrape_url">
        {% trans "Your website" %}
      </label>
      <div class="flex gap-2">
        <input id="id_scrape_url" type="url" name="scrape_url"
               placeholder="https://your-organisation.org.uk"
               class="flex-1 border-2 border-slate-200 rounded-lg px-4 py-2.5 text-sm focus:border-blue-800 focus:ring-2 focus:ring-blue-100 outline-none"
               value="{{ org.website }}">
        <button type="button" id="scrape-btn"
                hx-post="{% url 'onboarding_scrape' %}"
                hx-vals='js:{"url": document.getElementById("id_scrape_url").value}'
                hx-target="#scrape-result"
                hx-swap="innerHTML"
                hx-indicator="#scrape-spinner"
                class="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-800 text-white text-sm font-bold hover:bg-blue-900 min-h-[44px] whitespace-nowrap">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          {% trans "Populate from website" %}
        </button>
      </div>
      <div id="scrape-spinner" class="htmx-indicator mt-2 text-sm text-blue-700 flex items-center gap-2">
        <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/></svg>
        {% trans "Scanning your website with AI…" %}
      </div>
      <div id="scrape-result"></div>
      <p class="text-xs text-slate-400 mt-1.5">
        {% trans "No website?" %} <a href="#" onclick="document.getElementById('id_scrape_url').value=''; return false;" class="text-blue-700 font-semibold underline">{% trans "Fill in manually below" %}</a>
      </p>
    </div>

    <hr class="border-slate-100 mb-6">

    <form id="step-form" method="post" enctype="multipart/form-data">
      {% csrf_token %}
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">

        {{! Name }}
        <div class="sm:col-span-2">
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1" for="{{ form.name.id_for_label }}">
            {{ form.name.label }}
            {% if form.name.value %}<span class="ms-2 text-xs bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded font-bold">{% trans "Imported" %}</span>{% endif %}
          </label>
          {{ form.name }}
          {% if form.name.errors %}<p class="text-xs text-red-600 mt-1">{{ form.name.errors.0 }}</p>{% endif %}
        </div>

        {{! Short description }}
        <div class="sm:col-span-2">
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1" for="{{ form.short_description.id_for_label }}">
            {{ form.short_description.label }}
          </label>
          {{ form.short_description }}
        </div>

        {{! Description }}
        <div class="sm:col-span-2">
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1" for="{{ form.description.id_for_label }}">
            {{ form.description.label }}
          </label>
          {{ form.description }}
        </div>

        {{! Email }}
        <div>
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1" for="{{ form.email.id_for_label }}">{{ form.email.label }}</label>
          {{ form.email }}
        </div>

        {{! Phone }}
        <div>
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1" for="{{ form.phone.id_for_label }}">{{ form.phone.label }}</label>
          {{ form.phone }}
        </div>

        {{! Address }}
        <div>
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1" for="{{ form.address_line_1.id_for_label }}">{% trans "Address" %}</label>
          {{ form.address_line_1 }}
        </div>
        <div>
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1" for="{{ form.city.id_for_label }}">{% trans "City" %}</label>
          {{ form.city }}
        </div>
        <div>
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1" for="{{ form.postcode.id_for_label }}">{% trans "Postcode" %}</label>
          {{ form.postcode }}
        </div>

        {{! Logo }}
        <div>
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1">{% trans "Logo" %}</label>
          {{ form.logo }}
          <p class="text-xs text-slate-400 mt-1">{% trans "Optional — not scraped, always uploaded manually" %}</p>
        </div>

      </div>
    </form>
  </div>
  {% endblock %}

  {% block wizard_js %}
  <script>
  // Populate form fields from HTMX JSON scrape response
  document.body.addEventListener("htmx:afterRequest", function(evt) {
    if (!evt.detail.target || evt.detail.target.id !== "scrape-result") return;
    try {
      const data = JSON.parse(evt.detail.xhr.responseText);
      if (data.error) {
        document.getElementById("scrape-result").innerHTML =
          '<p class="text-sm text-red-600 mt-2 bg-red-50 rounded-lg px-3 py-2">' + data.error + '</p>';
        return;
      }
      const fields = ["name","short_description","description","phone","email","address_line_1","city","postcode"];
      fields.forEach(f => {
        const el = document.getElementById("id_" + f);
        if (el && data[f]) { el.value = data[f]; el.classList.add("border-amber-400","bg-amber-50"); }
      });
      // Store suggested category IDs and events_page_url in hidden inputs for next steps
      let hidden = document.getElementById("scrape-meta");
      if (!hidden) { hidden = document.createElement("div"); hidden.id = "scrape-meta"; document.getElementById("step-form").appendChild(hidden); }
      hidden.dataset.suggestedIds = JSON.stringify(data.suggested_category_ids || []);
      hidden.dataset.eventsPageUrl = data.events_page_url || "";
      hidden.dataset.newsPgeUrl = data.news_page_url || "";
      // Show success banner
      let banner = '<div class="mt-3 flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl px-4 py-3">';
      banner += '<span class="text-green-600 text-lg">✓</span>';
      banner += '<div><p class="text-sm font-semibold text-green-800">{% trans "AI scan complete — review and edit anything above" %}</p>';
      if (data.events_found > 0) {
        banner += '<p class="text-xs text-green-700">' + data.events_found + ' {% trans "upcoming events saved as drafts" %} · ';
      }
      if (data.suggested_category_ids && data.suggested_category_ids.length > 0) {
        banner += data.suggested_category_ids.length + ' {% trans "services suggested on next step" %}';
      }
      banner += '</p></div></div>';
      document.getElementById("scrape-result").innerHTML = banner;
    } catch(e) { console.warn("Scrape parse error", e); }
  });
  </script>
  {% endblock %}
  ```

- [ ] **Step 4: Apply Tailwind form classes in `OnboardingAboutForm`**

  In `apps/organizations/forms.py`, update `OnboardingAboutForm`:

  ```python
  _INPUT_CLASS = "block w-full border-2 border-slate-200 rounded-lg px-3 py-2.5 text-sm focus:border-blue-800 focus:ring-2 focus:ring-blue-100 outline-none font-body"
  _TEXTAREA_CLASS = _INPUT_CLASS + " resize-y"

  class OnboardingAboutForm(forms.ModelForm):
      class Meta:
          model = Organization
          fields = [
              "name", "short_description", "description",
              "logo", "website", "email", "phone",
              "address_line_1", "address_line_2", "city", "postcode",
          ]
          widgets = {
              "name": forms.TextInput(attrs={"class": _INPUT_CLASS}),
              "short_description": forms.Textarea(attrs={"rows": 2, "class": _TEXTAREA_CLASS}),
              "description": forms.Textarea(attrs={"rows": 5, "class": _TEXTAREA_CLASS}),
              "website": forms.URLInput(attrs={"class": _INPUT_CLASS}),
              "email": forms.EmailInput(attrs={"class": _INPUT_CLASS}),
              "phone": forms.TextInput(attrs={"class": _INPUT_CLASS}),
              "address_line_1": forms.TextInput(attrs={"class": _INPUT_CLASS}),
              "address_line_2": forms.TextInput(attrs={"class": _INPUT_CLASS}),
              "city": forms.TextInput(attrs={"class": _INPUT_CLASS}),
              "postcode": forms.TextInput(attrs={"class": _INPUT_CLASS}),
          }
  ```

- [ ] **Step 5: Update `_step_about` view to pass `org` to context**

  In `apps/organizations/onboarding_views.py`, find `_step_about` and ensure context includes:

  ```python
  context = {
      **_base_context("about", state, prev_step=None),
      "form": form,
      "org": org,
  }
  ```

- [ ] **Step 6: Run tests — confirm they pass**

  ```bash
  python manage.py test apps.organizations.tests.StepAboutTest --settings=config.settings.test
  ```

  Expected: `OK`

- [ ] **Step 7: Commit**

  ```bash
  git add apps/organizations/onboarding_views.py apps/organizations/forms.py templates/portal/onboarding/step_about.html
  git commit -m "feat: Step 1 Smart Import — Gemini scrape-first onboarding"
  ```

---

## Task 7: Step 2 — Services chip picker

**Files:**
- Modify: `apps/organizations/onboarding_views.py` (`_step_services`)
- Replace: `templates/portal/onboarding/step_services.html`
- Modify: `apps/organizations/tests.py`

- [ ] **Step 1: Write failing tests**

  ```python
  class StepServicesTest(TestCase):
      def setUp(self):
          self.org = _onboarding_org()
          self.user = _org_manager(self.org)
          state = _get_or_create_state(self.org)
          state.mark_step_complete("about")
          self.client.login(username="testmanager", password="testpass")

      def test_step_services_get_shows_categories(self):
          from apps.services.models import ServiceCategory
          ServiceCategory.objects.create(name="Mental Health", slug="mental-health", display_order=1)
          resp = self.client.get("/portal/onboarding/services/")
          self.assertEqual(resp.status_code, 200)
          self.assertContains(resp, "Mental Health")

      def test_step_services_post_saves_areas_and_advances(self):
          from apps.core.models import GeographicArea
          area = GeographicArea.objects.create(name="Wolverhampton", slug="wolverhampton")
          resp = self.client.post("/portal/onboarding/services/", {
              "areas_served": [area.pk],
              "selected_categories": "",
          })
          self.assertRedirects(resp, "/portal/onboarding/referral_config/")
  ```

- [ ] **Step 2: Run tests — confirm they fail**

  ```bash
  python manage.py test apps.organizations.tests.StepServicesTest --settings=config.settings.test
  ```

- [ ] **Step 3: Update `_step_services` view in `apps/organizations/onboarding_views.py`**

  Replace `_step_services` with:

  ```python
  def _step_services(request, org, state):
      from apps.services.models import ServiceCategory
      from apps.core.models import GeographicArea

      categories = ServiceCategory.objects.filter(is_active=True).order_by("display_order", "name")
      areas = GeographicArea.objects.all().order_by("name")
      suggested_ids = request.session.get("scrape_suggested_ids", [])

      if request.method == "POST":
          selected_cat_ids = [
              int(x) for x in request.POST.get("selected_categories", "").split(",") if x.strip()
          ]
          selected_area_ids = request.POST.getlist("areas_served")

          # Delete existing services, recreate from selected categories
          org.services.all().delete()
          for cat_id in selected_cat_ids:
              try:
                  cat = ServiceCategory.objects.get(pk=cat_id)
                  OrganizationService.objects.create(
                      organization=org,
                      name=cat.name,
                      category=cat,
                      support_stream=cat.support_stream,
                  )
              except ServiceCategory.DoesNotExist:
                  pass

          org.areas_served.set(selected_area_ids)
          org.save(update_fields=["updated_at"])
          state.mark_step_complete("services")
          return redirect("organizations:onboarding_step", step="referral_config")

      selected_cat_ids = list(org.services.values_list("category_id", flat=True))

      context = {
          **_base_context("services", state, prev_step="about"),
          "categories": categories,
          "areas": areas,
          "selected_cat_ids": selected_cat_ids,
          "suggested_ids": suggested_ids,
          "selected_area_ids": list(org.areas_served.values_list("id", flat=True)),
      }
      return render(request, "portal/onboarding/step_services.html", context)
  ```

- [ ] **Step 4: Replace `templates/portal/onboarding/step_services.html`**

  ```html
  {% extends "portal/onboarding/base_wizard.html" %}
  {% load i18n %}

  {% block step_content %}
  <div class="px-8 py-8">
    <h2 class="font-heading text-xl font-bold text-slate-800 mb-1">{% trans "Services you offer" %}</h2>
    <p class="text-sm text-slate-500 mb-2">{% trans "Select every service category that applies. AI suggestions are highlighted." %}</p>

    {% if suggested_ids %}
    <div class="mb-4 flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
      <span>⭐</span> {% trans "Amber chips were suggested from your website — click to confirm or deselect." %}
    </div>
    {% endif %}

    {{! Search }}
    <input type="text" id="cat-search" placeholder="{% trans 'Search services…' %}"
           class="block w-full border-2 border-slate-200 rounded-lg px-4 py-2.5 text-sm mb-4 focus:border-blue-800 outline-none"
           oninput="filterChips(this.value)">

    {{! Chip grid }}
    <div id="chip-grid" class="flex flex-wrap gap-2 mb-8">
      {% for cat in categories %}
      <button type="button"
              data-cat-id="{{ cat.id }}"
              data-name="{{ cat.name|lower }}"
              onclick="toggleChip(this)"
              class="chip inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border-2 transition-all min-h-[36px]
                {% if cat.id in selected_cat_ids %}selected border-blue-800 bg-blue-800 text-white
                {% elif cat.id in suggested_ids %}suggested border-amber-400 bg-amber-50 text-amber-800
                {% else %}border-slate-200 bg-white text-slate-600 hover:border-blue-300{% endif %}">
        {% if cat.id in suggested_ids and cat.id not in selected_cat_ids %}<span>⭐</span>{% endif %}
        {% if cat.id in selected_cat_ids %}<span>✓</span>{% endif %}
        {{ cat.name }}
      </button>
      {% endfor %}
    </div>

    {{! Geographic coverage }}
    <div class="border-t border-slate-100 pt-6 mb-6">
      <h3 class="font-heading text-base font-bold text-slate-700 mb-3">{% trans "Areas covered" %}</h3>
      <div class="flex flex-wrap gap-2">
        {% for area in areas %}
        <label class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border-2 cursor-pointer text-sm font-medium transition-all
                      {% if area.id in selected_area_ids %}border-blue-800 bg-blue-800 text-white{% else %}border-slate-200 bg-white text-slate-600 hover:border-blue-300{% endif %}">
          <input type="checkbox" name="areas_served" value="{{ area.pk }}"
                 {% if area.id in selected_area_ids %}checked{% endif %}
                 class="sr-only" onchange="this.closest('label').classList.toggle('border-blue-800'); this.closest('label').classList.toggle('bg-blue-800'); this.closest('label').classList.toggle('text-white'); this.closest('label').classList.toggle('text-slate-600');">
          {{ area.name }}
        </label>
        {% endfor %}
      </div>
    </div>

    <form id="step-form" method="post">
      {% csrf_token %}
      <input type="hidden" name="selected_categories" id="selected-categories-input" value="{{ selected_cat_ids|join:',' }}">
    </form>
  </div>
  {% endblock %}

  {% block wizard_js %}
  <script>
  const selected = new Set({{ selected_cat_ids|safe }});
  const suggested = new Set({{ suggested_ids|safe }});

  function toggleChip(btn) {
    const id = parseInt(btn.dataset.catId);
    if (selected.has(id)) {
      selected.delete(id);
      btn.classList.remove("border-blue-800","bg-blue-800","text-white");
      if (suggested.has(id)) {
        btn.classList.add("border-amber-400","bg-amber-50","text-amber-800");
      } else {
        btn.classList.add("border-slate-200","bg-white","text-slate-600");
      }
      btn.querySelector("span:first-child")?.remove();
    } else {
      selected.add(id);
      btn.classList.remove("border-slate-200","bg-white","text-slate-600","border-amber-400","bg-amber-50","text-amber-800");
      btn.classList.add("border-blue-800","bg-blue-800","text-white");
    }
    document.getElementById("selected-categories-input").value = [...selected].join(",");
  }

  function filterChips(query) {
    document.querySelectorAll(".chip").forEach(btn => {
      btn.style.display = btn.dataset.name.includes(query.toLowerCase()) ? "" : "none";
    });
  }
  </script>
  {% endblock %}
  ```

- [ ] **Step 5: Run tests — confirm they pass**

  ```bash
  python manage.py test apps.organizations.tests.StepServicesTest --settings=config.settings.test
  ```

  Expected: `OK`

- [ ] **Step 6: Commit**

  ```bash
  git add apps/organizations/onboarding_views.py templates/portal/onboarding/step_services.html apps/organizations/tests.py
  git commit -m "feat: Step 2 Services — chip picker with AI suggestions"
  ```

---

## Task 8: Step 3 — Referral Setup (dual tabs + drag-and-drop builder)

**Files:**
- Modify: `apps/organizations/onboarding_views.py` (`_step_referral_config`)
- Replace: `templates/portal/onboarding/step_referral_config.html`
- Modify: `apps/organizations/tests.py`

- [ ] **Step 1: Write failing tests**

  ```python
  class StepReferralConfigTest(TestCase):
      def setUp(self):
          self.org = _onboarding_org()
          self.user = _org_manager(self.org)
          state = _get_or_create_state(self.org)
          state.mark_step_complete("about")
          state.mark_step_complete("services")
          self.client.login(username="testmanager", password="testpass")

      def test_referral_config_get_renders_dual_tabs(self):
          resp = self.client.get("/portal/onboarding/referral_config/")
          self.assertEqual(resp.status_code, 200)
          self.assertContains(resp, "Self-referral")
          self.assertContains(resp, "Organisation referral")

      def test_referral_config_post_saves_channels_and_fields(self):
          resp = self.client.post("/portal/onboarding/referral_config/", {
              "self_referral_channels": ["in_platform", "email"],
              "self_referral_email": "self@example.org",
              "professional_referral_channels": ["in_platform"],
              "professional_referral_email": "",
              "fields_json": '[{"label":"Full name","field_type":"text","form_type":"both","is_required":true,"display_order":1}]',
          })
          self.assertRedirects(resp, "/portal/onboarding/scraping/")
          self.org.refresh_from_db()
          self.assertIn("in_platform", self.org.self_referral_channels)
          self.assertEqual(self.org.self_referral_email, "self@example.org")
          field = ReferralFormField.objects.filter(organization=self.org).first()
          self.assertIsNotNone(field)
          self.assertEqual(field.label, "Full name")
  ```

- [ ] **Step 2: Run tests — confirm they fail**

  ```bash
  python manage.py test apps.organizations.tests.StepReferralConfigTest --settings=config.settings.test
  ```

- [ ] **Step 3: Update `_step_referral_config` view**

  ```python
  def _step_referral_config(request, org, state):
      if request.method == "POST":
          # Delivery channels per form type
          org.self_referral_channels = request.POST.getlist("self_referral_channels")
          org.professional_referral_channels = request.POST.getlist("professional_referral_channels")
          org.self_referral_email = request.POST.get("self_referral_email", "")
          org.professional_referral_email = request.POST.get("professional_referral_email", "")
          org.crm_webhook_url = request.POST.get("crm_webhook_url", "")
          org.crm_webhook_secret = request.POST.get("crm_webhook_secret", "")
          org.save(update_fields=[
              "self_referral_channels", "professional_referral_channels",
              "self_referral_email", "professional_referral_email",
              "crm_webhook_url", "crm_webhook_secret", "updated_at",
          ])

          # Rebuild referral form fields from JSON payload
          fields_json = request.POST.get("fields_json", "[]")
          try:
              fields_data = json.loads(fields_json)
          except (ValueError, TypeError):
              fields_data = []

          # Clear existing, recreate (preserve GDPR consent at end)
          ReferralFormField.objects.filter(organization=org).exclude(
              field_type="consent"
          ).delete()

          for idx, fdata in enumerate(fields_data):
              if fdata.get("field_type") == "consent":
                  continue  # GDPR consent managed separately
              ReferralFormField.objects.update_or_create(
                  organization=org,
                  label=fdata.get("label", "Field"),
                  defaults={
                      "field_type": fdata.get("field_type", "text"),
                      "form_type": fdata.get("form_type", "both"),
                      "is_required": fdata.get("is_required", False),
                      "display_order": idx,
                      "help_text": fdata.get("help_text", ""),
                      "placeholder": fdata.get("placeholder", ""),
                      "is_active": True,
                  }
              )

          # Ensure GDPR consent exists, pinned at end
          max_order = ReferralFormField.objects.filter(organization=org).count()
          ReferralFormField.objects.get_or_create(
              organization=org,
              field_type="consent",
              defaults={
                  "label": str(_("I consent to my information being shared for referral purposes")),
                  "is_required": True,
                  "display_order": max_order + 1,
                  "form_type": "both",
              }
          )

          state.mark_step_complete("referral_config")
          return redirect("organizations:onboarding_step", step="scraping")

      existing_fields = list(
          ReferralFormField.objects.filter(organization=org)
          .exclude(field_type="consent")
          .order_by("display_order")
          .values("label", "field_type", "form_type", "is_required", "help_text", "placeholder")
      )

      context = {
          **_base_context("referral_config", state, prev_step="services"),
          "org": org,
          "existing_fields_json": json.dumps(existing_fields),
          "DELIVERY_CHANNELS": [
              ("in_platform", _("Platform inbox"), _("Referrals appear in your portal — always enabled"), True),
              ("email", _("Email"), _("Receive referrals by email"), False),
              ("csv", _("CSV export"), _("Download referrals as a spreadsheet"), False),
              ("print", _("Print PDF"), _("Referrers can print a PDF copy"), False),
              ("crm_webhook", _("CRM Webhook"), _("Post referrals to your CRM system"), False),
          ],
      }
      return render(request, "portal/onboarding/step_referral_config.html", context)
  ```

- [ ] **Step 4: Replace `templates/portal/onboarding/step_referral_config.html`**

  ```html
  {% extends "portal/onboarding/base_wizard.html" %}
  {% load i18n %}

  {% block step_content %}
  <div class="px-8 py-8">
    <h2 class="font-heading text-xl font-bold text-slate-800 mb-1">{% trans "Referral setup" %}</h2>
    <p class="text-sm text-slate-500 mb-6">{% trans "Set up how you receive referrals and what information you need." %}</p>

    {{! Form type tabs }}
    <div class="flex border-b border-slate-200 mb-6" role="tablist">
      <button type="button" role="tab" aria-selected="true" onclick="switchTab('self', this)"
              id="tab-self" class="tab-btn px-5 py-2.5 text-sm font-semibold text-blue-800 border-b-2 border-blue-800">
        {% trans "Self-referral" %}
      </button>
      <button type="button" role="tab" aria-selected="false" onclick="switchTab('professional', this)"
              id="tab-professional" class="tab-btn px-5 py-2.5 text-sm font-semibold text-slate-400 border-b-2 border-transparent hover:text-slate-700">
        {% trans "Organisation referral" %}
      </button>
    </div>

    <form id="step-form" method="post">
      {% csrf_token %}

      {{! ---- SELF-REFERRAL TAB ---- }}
      <div id="panel-self" role="tabpanel">
        <h3 class="font-heading text-sm font-bold text-slate-600 uppercase tracking-wide mb-3">{% trans "Delivery channels" %}</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
          {% for key, label, desc, locked in DELIVERY_CHANNELS %}
          <label class="flex items-start gap-3 p-4 rounded-xl border-2 cursor-pointer
                        {% if key == 'in_platform' %}border-blue-200 bg-blue-50{% else %}border-slate-200 bg-white hover:border-blue-200{% endif %}">
            <input type="checkbox" name="self_referral_channels" value="{{ key }}"
                   {% if key == 'in_platform' %}checked disabled{% endif %}
                   {% if key in org.self_referral_channels %}checked{% endif %}
                   class="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-800"
                   onchange="toggleChannelConfig('self-{{ key }}', this.checked)">
            <div class="flex-1">
              <div class="text-sm font-semibold text-slate-800">
                {{ label }}
                {% if locked %}<span class="ms-2 text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">{% trans "Always on" %}</span>{% endif %}
              </div>
              <div class="text-xs text-slate-500 mt-0.5">{{ desc }}</div>
              {% if key == 'email' %}
              <div id="self-config-email" class="mt-2 {% if 'email' not in org.self_referral_channels %}hidden{% endif %}">
                <input type="email" name="self_referral_email" value="{{ org.self_referral_email }}"
                       placeholder="referrals@yourorg.org"
                       class="block w-full border border-slate-200 rounded-lg px-3 py-2 text-sm mt-1">
              </div>
              {% endif %}
              {% if key == 'crm_webhook' %}
              <div id="self-config-crm_webhook" class="mt-2 {% if 'crm_webhook' not in org.self_referral_channels %}hidden{% endif %}">
                <input type="url" name="crm_webhook_url" value="{{ org.crm_webhook_url }}" placeholder="https://your-crm.com/webhook"
                       class="block w-full border border-slate-200 rounded-lg px-3 py-2 text-sm mt-1 mb-1">
                <input type="text" name="crm_webhook_secret" value="{{ org.crm_webhook_secret }}" placeholder="{% trans 'Webhook secret (optional)' %}"
                       class="block w-full border border-slate-200 rounded-lg px-3 py-2 text-sm">
              </div>
              {% endif %}
            </div>
          </label>
          {% endfor %}
        </div>

        <h3 class="font-heading text-sm font-bold text-slate-600 uppercase tracking-wide mb-3">{% trans "Form fields — Self-referral" %}</h3>
        <p class="text-xs text-slate-500 mb-3">{% trans "Drag field types from the palette onto the canvas to build your form." %}</p>
        {% include "portal/onboarding/_form_builder.html" with form_type="self" %}
      </div>

      {{! ---- PROFESSIONAL REFERRAL TAB ---- }}
      <div id="panel-professional" role="tabpanel" class="hidden">
        <h3 class="font-heading text-sm font-bold text-slate-600 uppercase tracking-wide mb-3">{% trans "Delivery channels" %}</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-6">
          {% for key, label, desc, locked in DELIVERY_CHANNELS %}
          <label class="flex items-start gap-3 p-4 rounded-xl border-2 cursor-pointer
                        {% if key == 'in_platform' %}border-blue-200 bg-blue-50{% else %}border-slate-200 bg-white hover:border-blue-200{% endif %}">
            <input type="checkbox" name="professional_referral_channels" value="{{ key }}"
                   {% if key == 'in_platform' %}checked disabled{% endif %}
                   {% if key in org.professional_referral_channels %}checked{% endif %}
                   class="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-800"
                   onchange="toggleChannelConfig('pro-{{ key }}', this.checked)">
            <div class="flex-1">
              <div class="text-sm font-semibold text-slate-800">
                {{ label }}
                {% if locked %}<span class="ms-2 text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">{% trans "Always on" %}</span>{% endif %}
              </div>
              <div class="text-xs text-slate-500 mt-0.5">{{ desc }}</div>
              {% if key == 'email' %}
              <div id="pro-config-email" class="mt-2 {% if 'email' not in org.professional_referral_channels %}hidden{% endif %}">
                <input type="email" name="professional_referral_email" value="{{ org.professional_referral_email }}"
                       placeholder="referrals@yourorg.org"
                       class="block w-full border border-slate-200 rounded-lg px-3 py-2 text-sm mt-1">
              </div>
              {% endif %}
            </div>
          </label>
          {% endfor %}
        </div>

        <h3 class="font-heading text-sm font-bold text-slate-600 uppercase tracking-wide mb-3">{% trans "Form fields — Organisation referral" %}</h3>
        {% include "portal/onboarding/_form_builder.html" with form_type="professional" %}
      </div>

      {{! Hidden JSON payload submitted on save }}
      <input type="hidden" name="fields_json" id="fields-json-input" value="{{ existing_fields_json }}">

    </form>
  </div>
  {% endblock %}

  {% block wizard_js %}
  <script>
  function switchTab(name, btn) {
    document.querySelectorAll('[role="tabpanel"]').forEach(p => p.classList.add("hidden"));
    document.querySelectorAll(".tab-btn").forEach(b => {
      b.classList.remove("text-blue-800","border-blue-800");
      b.classList.add("text-slate-400","border-transparent");
    });
    document.getElementById("panel-" + name).classList.remove("hidden");
    btn.classList.add("text-blue-800","border-blue-800");
    btn.classList.remove("text-slate-400","border-transparent");
  }

  function toggleChannelConfig(id, show) {
    const el = document.getElementById("config-" + id);
    if (el) el.classList.toggle("hidden", !show);
    // Also handle the direct id pattern used in template
    const el2 = document.getElementById(id.replace("self-","self-config-").replace("pro-","pro-config-"));
    if (el2) el2.classList.toggle("hidden", !show);
  }

  // Form builder state: { self: [...fields], professional: [...fields] }
  let formFields = { self: [], professional: [] };
  try { formFields.self = JSON.parse('{{ existing_fields_json|escapejs }}').filter(f => f.form_type === "self" || f.form_type === "both"); } catch(e) {}
  try { formFields.professional = JSON.parse('{{ existing_fields_json|escapejs }}').filter(f => f.form_type === "professional" || f.form_type === "both"); } catch(e) {}

  const PALETTE_FIELDS = [
    { type: "text", label: "Name", icon: "✏️" },
    { type: "email", label: "Email", icon: "📧" },
    { type: "phone", label: "Phone", icon: "📱" },
    { type: "date", label: "Date of Birth", icon: "📅" },
    { type: "nhs_number", label: "NHS Number", icon: "🏥" },
    { type: "ni_number", label: "NI Number", icon: "🔑" },
    { type: "dbs_number", label: "DBS Number", icon: "🛡" },
    { type: "textarea", label: "Free text", icon: "📝" },
    { type: "checkbox", label: "Yes / No", icon: "☑️" },
    { type: "file", label: "File upload", icon: "📎" },
    { type: "select", label: "Dropdown", icon: "▼" },
  ];

  function addFieldToCanvas(fieldType, formType, customLabel) {
    const palField = PALETTE_FIELDS.find(f => f.type === fieldType);
    const label = customLabel || (palField ? palField.label : fieldType);
    formFields[formType].push({ field_type: fieldType, label: label, form_type: formType, is_required: false, help_text: "", placeholder: "" });
    renderCanvas(formType);
    syncJson();
  }

  function removeField(formType, idx) {
    formFields[formType].splice(idx, 1);
    renderCanvas(formType);
    syncJson();
  }

  function toggleRequired(formType, idx, checked) {
    formFields[formType][idx].is_required = checked;
    syncJson();
  }

  function updateLabel(formType, idx, val) {
    formFields[formType][idx].label = val;
    syncJson();
  }

  function renderCanvas(formType) {
    const canvas = document.getElementById("canvas-" + formType);
    if (!canvas) return;
    canvas.innerHTML = "";
    formFields[formType].forEach((field, idx) => {
      const palField = PALETTE_FIELDS.find(f => f.type === field.field_type);
      const icon = palField ? palField.icon : "📄";
      const div = document.createElement("div");
      div.className = "canvas-field flex items-center gap-3 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 mb-2";
      div.dataset.idx = idx;
      div.innerHTML = `
        <span class="drag-handle cursor-grab text-slate-300 text-lg select-none">⠿</span>
        <span class="text-lg">${icon}</span>
        <input type="text" value="${field.label}" onchange="updateLabel('${formType}', ${idx}, this.value)"
               class="flex-1 text-sm font-medium text-slate-800 bg-transparent border-b border-transparent hover:border-slate-300 focus:border-blue-500 outline-none py-0.5">
        <span class="text-xs bg-slate-200 text-slate-600 px-2 py-0.5 rounded">${field.field_type}</span>
        <label class="flex items-center gap-1 text-xs text-slate-500 cursor-pointer">
          <input type="checkbox" ${field.is_required ? "checked" : ""} onchange="toggleRequired('${formType}', ${idx}, this.checked)" class="h-3 w-3">
          Required
        </label>
        <button type="button" onclick="removeField('${formType}', ${idx})" class="text-slate-300 hover:text-red-500 text-lg leading-none" aria-label="Remove field">×</button>
      `;
      canvas.appendChild(div);
    });

    // GDPR consent — always pinned, cannot remove
    const gdpr = document.createElement("div");
    gdpr.className = "flex items-center gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mt-2";
    gdpr.innerHTML = `<span class="text-lg">🔒</span><span class="flex-1 text-sm font-medium text-amber-800">{% trans "GDPR consent" %} — {% trans "I consent to my information being shared" %}</span><span class="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded font-bold">{% trans "Always required" %}</span>`;
    canvas.appendChild(gdpr);

    // Init Sortable
    if (window.Sortable) {
      Sortable.create(canvas, {
        handle: ".drag-handle",
        animation: 150,
        onEnd: function(evt) {
          const moved = formFields[formType].splice(evt.oldIndex, 1)[0];
          formFields[formType].splice(evt.newIndex, 0, moved);
          formFields[formType].forEach((f, i) => { f.display_order = i; });
          syncJson();
        }
      });
    }
  }

  function syncJson() {
    const allFields = [
      ...formFields.self.map(f => ({...f, form_type: "self"})),
      ...formFields.professional.filter(f => !formFields.self.find(sf => sf.label === f.label && sf.field_type === f.field_type))
                                  .map(f => ({...f, form_type: "professional"})),
    ];
    document.getElementById("fields-json-input").value = JSON.stringify(allFields);
  }

  // Render canvases on load
  document.addEventListener("DOMContentLoaded", function() {
    ["self","professional"].forEach(ft => renderCanvas(ft));
  });
  </script>
  {% endblock %}
  ```

- [ ] **Step 5: Create `templates/portal/onboarding/_form_builder.html` partial**

  ```html
  {% load i18n %}
  {{! Palette }}
  <div class="flex flex-wrap gap-2 mb-4 p-3 bg-slate-50 rounded-xl border border-dashed border-slate-300">
    <span class="text-xs font-bold text-slate-400 uppercase tracking-wide w-full mb-1">{% trans "Add fields" %}</span>
    <button type="button" onclick="addFieldToCanvas('text','{{ form_type }}')" class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-400 cursor-pointer">✏️ {% trans "Name" %}</button>
    <button type="button" onclick="addFieldToCanvas('email','{{ form_type }}')" class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-400 cursor-pointer">📧 {% trans "Email" %}</button>
    <button type="button" onclick="addFieldToCanvas('phone','{{ form_type }}')" class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-400 cursor-pointer">📱 {% trans "Phone" %}</button>
    <button type="button" onclick="addFieldToCanvas('date','{{ form_type }}')" class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-400 cursor-pointer">📅 {% trans "Date of Birth" %}</button>
    <button type="button" onclick="addFieldToCanvas('nhs_number','{{ form_type }}')" class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-400 cursor-pointer">🏥 {% trans "NHS No." %}</button>
    <button type="button" onclick="addFieldToCanvas('ni_number','{{ form_type }}')" class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-400 cursor-pointer">🔑 {% trans "NI No." %}</button>
    <button type="button" onclick="addFieldToCanvas('textarea','{{ form_type }}')" class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-400 cursor-pointer">📝 {% trans "Free text" %}</button>
    <button type="button" onclick="addFieldToCanvas('checkbox','{{ form_type }}')" class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-400 cursor-pointer">☑️ {% trans "Yes/No" %}</button>
    <button type="button" onclick="addFieldToCanvas('file','{{ form_type }}')" class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-400 cursor-pointer">📎 {% trans "File upload" %}</button>
    <button type="button" onclick="addFieldToCanvas('select','{{ form_type }}')" class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-400 cursor-pointer">▼ {% trans "Dropdown" %}</button>
    <button type="button"
            onclick="const lbl=prompt('{% trans "Custom field name:" %}'); if(lbl) addFieldToCanvas('text','{{ form_type }}', lbl);"
            class="pal-chip inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 border border-amber-300 rounded-lg text-sm text-amber-800 hover:border-amber-500 cursor-pointer">+ {% trans "Custom field" %}</button>
  </div>

  {{! Canvas }}
  <div id="canvas-{{ form_type }}" class="min-h-[80px] border-2 border-dashed border-slate-200 rounded-xl p-3 bg-white">
    <p class="text-sm text-slate-400 text-center py-4" id="canvas-empty-{{ form_type }}">{% trans "Drag or click field types above to add them" %}</p>
  </div>
  ```

- [ ] **Step 6: Run tests — confirm they pass**

  ```bash
  python manage.py test apps.organizations.tests.StepReferralConfigTest --settings=config.settings.test
  ```

  Expected: `OK`

- [ ] **Step 7: Commit**

  ```bash
  git add apps/organizations/onboarding_views.py templates/portal/onboarding/step_referral_config.html templates/portal/onboarding/_form_builder.html apps/organizations/tests.py
  git commit -m "feat: Step 3 Referral Setup — dual tabs, drag-and-drop form builder"
  ```

---

## Task 9: Steps 4 & 5 — Website Config and Review & Publish

**Files:**
- Modify: `apps/organizations/onboarding_views.py` (`_step_scraping`, `_step_review`)
- Replace: `templates/portal/onboarding/step_scraping.html`
- Replace: `templates/portal/onboarding/step_review.html`
- Modify: `apps/organizations/tests.py`

- [ ] **Step 1: Write failing tests**

  ```python
  class StepScrapingTest(TestCase):
      def setUp(self):
          self.org = _onboarding_org()
          self.user = _org_manager(self.org)
          state = _get_or_create_state(self.org)
          for s in ["about","services","referral_config"]:
              state.mark_step_complete(s)
          self.client.login(username="testmanager", password="testpass")

      def test_scraping_step_get_renders(self):
          resp = self.client.get("/portal/onboarding/scraping/")
          self.assertEqual(resp.status_code, 200)
          self.assertContains(resp, "events_page_url")

      def test_scraping_step_skip_still_advances(self):
          resp = self.client.post("/portal/onboarding/scraping/", {"skip": "1"})
          self.assertRedirects(resp, "/portal/onboarding/review/")
          state = OrgOnboardingState.objects.get(organization=self.org)
          self.assertIn("scraping", state.completed_steps)

  class StepReviewPublishTest(TestCase):
      def setUp(self):
          self.org = _onboarding_org()
          self.user = _org_manager(self.org)
          state = _get_or_create_state(self.org)
          _complete_all_steps(state)
          self.client.login(username="testmanager", password="testpass")

      def test_publish_sets_org_active(self):
          resp = self.client.post("/portal/onboarding/review/")
          self.org.refresh_from_db()
          self.assertEqual(self.org.status, "active")

      def test_publish_redirects_to_dashboard(self):
          resp = self.client.post("/portal/onboarding/review/")
          self.assertRedirects(resp, "/portal/dashboard/")
  ```

- [ ] **Step 2: Run tests — confirm they fail**

  ```bash
  python manage.py test apps.organizations.tests.StepScrapingTest apps.organizations.tests.StepReviewPublishTest --settings=config.settings.test
  ```

- [ ] **Step 3: Update `_step_scraping` view to handle skip and pre-fill from session**

  ```python
  def _step_scraping(request, org, state):
      if request.method == "POST":
          if request.POST.get("skip"):
              state.mark_step_complete("scraping")
              return redirect("organizations:onboarding_step", step="review")

          form = OnboardingScrapingForm(request.POST, instance=org)
          if form.is_valid():
              form.save()
              state.mark_step_complete("scraping")
              return redirect("organizations:onboarding_step", step="review")
      else:
          # Pre-fill from scrape session data if available
          initial = {}
          if not org.events_page_url and request.session.get("scrape_url"):
              initial["events_page_url"] = request.session.get("scrape_events_url", "")
          form = OnboardingScrapingForm(instance=org, initial=initial)

      context = {
          **_base_context("scraping", state, prev_step="referral_config"),
          "form": form,
      }
      return render(request, "portal/onboarding/step_scraping.html", context)
  ```

- [ ] **Step 4: Replace `templates/portal/onboarding/step_scraping.html`**

  ```html
  {% extends "portal/onboarding/base_wizard.html" %}
  {% load i18n %}

  {% block step_content %}
  <div class="px-8 py-8">
    <h2 class="font-heading text-xl font-bold text-slate-800 mb-1">{% trans "Website scraping config" %}</h2>
    <p class="text-sm text-slate-500 mb-2">{% trans "We scan these pages weekly to keep your events and news up to date." %}</p>

    <div class="mb-6 flex items-start gap-3 bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 text-sm text-blue-800">
      <svg class="w-5 h-5 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
      {% trans "This step is optional — you can come back and set it up later from your portal settings." %}
    </div>

    <form id="step-form" method="post">
      {% csrf_token %}
      <div class="space-y-4 mb-6">
        <div>
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1.5" for="{{ form.events_page_url.id_for_label }}">
            {% trans "Events page URL" %}
          </label>
          {{ form.events_page_url }}
          <p class="text-xs text-slate-400 mt-1">{% trans "e.g. https://yourorg.org/events or /whats-on" %}</p>
        </div>
        <div>
          <label class="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-1.5" for="{{ form.news_page_url.id_for_label }}">
            {% trans "News / blog page URL" %}
          </label>
          {{ form.news_page_url }}
        </div>
      </div>
    </form>
  </div>
  {% endblock %}

  {% block nav_buttons %}
  <div class="flex items-center gap-3">
    <form method="post">{% csrf_token %}<input type="hidden" name="skip" value="1">
      <button type="submit" class="px-4 py-2.5 text-sm text-slate-500 hover:text-slate-700 min-h-[44px]">{% trans "Skip for now" %}</button>
    </form>
    <button type="submit" form="step-form" class="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-blue-800 text-white text-sm font-bold hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 min-h-[44px]">
      {% trans "Save & review" %} →
    </button>
  </div>
  {% endblock %}
  ```

- [ ] **Step 5: Replace `templates/portal/onboarding/step_review.html`**

  ```html
  {% extends "portal/onboarding/base_wizard.html" %}
  {% load i18n %}

  {% block step_content %}
  <div class="px-8 py-8">
    <h2 class="font-heading text-xl font-bold text-slate-800 mb-1">{% trans "Review & publish" %}</h2>
    <p class="text-sm text-slate-500 mb-6">{% trans "Check everything looks right, then publish your organisation." %}</p>

    {% if incomplete_steps %}
    <div class="mb-6 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-800">
      ⚠️ {% trans "Some steps aren't complete:" %}
      <ul class="mt-1 ms-4 list-disc text-xs">
        {% for step in incomplete_steps %}<li>{{ step }}</li>{% endfor %}
      </ul>
    </div>
    {% endif %}

    {{! Summary cards }}
    <div class="space-y-4 mb-8">
      <div class="rounded-xl border border-slate-200 p-5">
        <div class="flex justify-between items-start mb-3">
          <h3 class="font-heading text-sm font-bold text-slate-700 uppercase tracking-wide">{% trans "About" %}</h3>
          <a href="{% url 'organizations:onboarding_step' step='about' %}" class="text-xs text-blue-700 font-semibold hover:underline">✏️ {% trans "Edit" %}</a>
        </div>
        <p class="text-sm font-bold text-slate-800">{{ org.name }}</p>
        <p class="text-xs text-slate-500 mt-1">{{ org.short_description }}</p>
        {% if org.email %}<p class="text-xs text-slate-400 mt-1">{{ org.email }} · {{ org.phone }}</p>{% endif %}
      </div>

      <div class="rounded-xl border border-slate-200 p-5">
        <div class="flex justify-between items-start mb-3">
          <h3 class="font-heading text-sm font-bold text-slate-700 uppercase tracking-wide">{% trans "Services" %} ({{ services.count }})</h3>
          <a href="{% url 'organizations:onboarding_step' step='services' %}" class="text-xs text-blue-700 font-semibold hover:underline">✏️ {% trans "Edit" %}</a>
        </div>
        <div class="flex flex-wrap gap-1.5">
          {% for svc in services %}<span class="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">{{ svc.name }}</span>{% endfor %}
          {% if not services %}<span class="text-xs text-slate-400">{% trans "No services added" %}</span>{% endif %}
        </div>
      </div>

      <div class="rounded-xl border border-slate-200 p-5">
        <div class="flex justify-between items-start mb-3">
          <h3 class="font-heading text-sm font-bold text-slate-700 uppercase tracking-wide">{% trans "Referral setup" %}</h3>
          <a href="{% url 'organizations:onboarding_step' step='referral_config' %}" class="text-xs text-blue-700 font-semibold hover:underline">✏️ {% trans "Edit" %}</a>
        </div>
        <p class="text-xs text-slate-500">
          {% trans "Self-referral fields:" %} {{ self_fields.count }} ·
          {% trans "Organisation referral fields:" %} {{ pro_fields.count }}
        </p>
      </div>
    </div>

    <form method="post">
      {% csrf_token %}
      {% if can_publish %}
      <button type="submit"
              class="w-full inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-amber-500 text-white text-base font-bold hover:bg-amber-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500 min-h-[52px]">
        🚀 {% trans "Publish your organisation" %}
      </button>
      {% else %}
      <p class="text-sm text-slate-500 text-center">{% trans "Complete all required steps above to publish." %}</p>
      {% endif %}
    </form>
  </div>
  {% endblock %}

  {% block nav_buttons %}{% endblock %}
  ```

- [ ] **Step 6: Update `_step_review` view to pass `self_fields`, `pro_fields` context**

  In `apps/organizations/onboarding_views.py`, find `_step_review` and update context:

  ```python
  from apps.referrals.models import ReferralFormField

  # In _step_review:
  context = {
      **_base_context("review", state, prev_step="scraping"),
      "org": org,
      "services": org.services.filter(is_active=True),
      "self_fields": ReferralFormField.objects.filter(
          organization=org, form_type__in=["self", "both"]
      ).exclude(field_type="consent"),
      "pro_fields": ReferralFormField.objects.filter(
          organization=org, form_type__in=["professional", "both"]
      ).exclude(field_type="consent"),
      "incomplete_steps": [
          label for label, slug in STEP_LABELS
          if slug not in state.completed_steps and slug != "review"
      ],
      "can_publish": state.next_incomplete_step() is None or state.next_incomplete_step() == "review",
  }
  ```

  On POST success, add success message:

  ```python
  from django.contrib import messages
  messages.success(request, _("Your organisation is now live! Welcome to the platform."))
  ```

- [ ] **Step 7: Run tests — confirm they pass**

  ```bash
  python manage.py test apps.organizations.tests.StepScrapingTest apps.organizations.tests.StepReviewPublishTest --settings=config.settings.test
  ```

  Expected: `OK`

- [ ] **Step 8: Run full test suite**

  ```bash
  python manage.py test apps.organizations apps.referrals --settings=config.settings.test
  ```

  Expected: All pass.

- [ ] **Step 9: Commit**

  ```bash
  git add apps/organizations/onboarding_views.py templates/portal/onboarding/
  git commit -m "feat: Steps 4-5 — Website Config and Review & Publish redesign"
  ```

---

## Task 10: OrgDocument + RAG brain integration

> **Prerequisite:** Phase 6 Plan 01 must be executed first — this task requires `OrgDocument` model and `index_org_document` Celery task to exist.

**Files:**
- Modify: `apps/organizations/onboarding_views.py`
- Modify: `apps/events/tasks.py`
- Modify: `apps/organizations/tests.py`

- [ ] **Step 1: Write failing test**

  ```python
  from unittest.mock import patch

  class ScrapeOrgDocumentTest(TestCase):
      def setUp(self):
          self.org = _onboarding_org()
          self.user = _org_manager(self.org)
          self.client.login(username="testmanager", password="testpass")

      @patch("apps.organizations.onboarding_views.scrape_org_website")
      def test_scrape_endpoint_creates_org_document(self, mock_scrape):
          mock_scrape.return_value = {
              "name": "Test Org", "short_description": "x", "description": "y",
              "phone": "", "email": "", "address_line_1": "", "city": "", "postcode": "",
              "services": [], "events": [], "events_page_url": "", "news_page_url": "",
              "raw_text": "Full website content of test org",
          }
          self.client.post(
              "/portal/onboarding/scrape/",
              data={"url": "https://test.org"},
              HTTP_HX_REQUEST="true",
          )
          from apps.assistant.models import OrgDocument
          doc = OrgDocument.objects.filter(organization=self.org).first()
          self.assertIsNotNone(doc)
          self.assertEqual(doc.source_type, "website_scrape")
  ```

- [ ] **Step 2: Run test — confirm it fails (OrgDocument doesn't exist yet)**

  ```bash
  python manage.py test apps.organizations.tests.ScrapeOrgDocumentTest --settings=config.settings.test
  ```

  Expected: `ImportError: cannot import name 'OrgDocument'` — confirms Phase 6 Plan 01 is the prerequisite.

- [ ] **Step 3: After Phase 6 Plan 01 is done — add OrgDocument creation to `onboarding_scrape_view`**

  In `apps/organizations/onboarding_views.py`, inside `onboarding_scrape_view`, after `request.session["scrape_raw_text"] = ...` add:

  ```python
  # Save raw text as OrgDocument for RAG indexing
  org = _get_org_for_manager(request)
  if org and result.get("raw_text"):
      from apps.assistant.models import OrgDocument
      OrgDocument.objects.update_or_create(
          organization=org,
          source_type="website_scrape",
          defaults={
              "title": f"Website: {url}",
              "raw_text": result["raw_text"],
              "source_url": url,
          }
      )
      # Signal fires index_org_document.delay() automatically via post_save
  ```

- [ ] **Step 4: Extend `scrape_org_events` Celery task to refresh OrgDocument**

  In `apps/events/tasks.py`, find `scrape_org_events` and add after event creation:

  ```python
  # Refresh OrgDocument with latest website text
  try:
      from apps.organizations.scraping import scrape_org_website
      from apps.assistant.models import OrgDocument
      scrape_result = scrape_org_website(org.events_page_url)
      if scrape_result and scrape_result.get("raw_text"):
          OrgDocument.objects.update_or_create(
              organization=org,
              source_type="website_scrape",
              defaults={
                  "title": f"Website: {org.events_page_url}",
                  "raw_text": scrape_result["raw_text"],
                  "source_url": org.events_page_url,
              }
          )
  except Exception as exc:
      logger.warning("OrgDocument refresh failed for org %s: %s", org_id, exc)
  ```

- [ ] **Step 5: Run test — confirm it passes**

  ```bash
  python manage.py test apps.organizations.tests.ScrapeOrgDocumentTest --settings=config.settings.test
  ```

  Expected: `OK`

- [ ] **Step 6: Run full suite**

  ```bash
  python manage.py test apps.organizations apps.referrals apps.assistant apps.events --settings=config.settings.test
  ruff check apps/ -q
  ```

  Expected: All pass, no lint errors.

- [ ] **Step 7: Commit**

  ```bash
  git add apps/organizations/onboarding_views.py apps/events/tasks.py apps/organizations/tests.py
  git commit -m "feat: onboarding scrape feeds OrgDocument into RAG brain"
  ```

---

## Final verification checklist

- [ ] `python manage.py runserver` — navigate to `/en/portal/onboarding/about/` as a new org_manager
- [ ] Enter a real URL → "Populate from website" → fields pre-fill within 15 seconds
- [ ] Step 2: amber chips appear for suggested categories, chip search filters in real time
- [ ] Step 3: drag palette fields onto canvas, rename a field to "Client ID Number", toggle Required, switch to Organisation referral tab and build a second form
- [ ] Step 4: confirm events/news URLs pre-filled if detected; "Skip for now" advances without saving
- [ ] Step 5: summary cards show, Publish button sets org to active, success toast appears
- [ ] Events dashboard: scraped events appear as unpublished drafts
- [ ] `python manage.py test apps.organizations apps.referrals --settings=config.settings.test` → all pass
- [ ] `ruff check apps/ -q` → no errors
