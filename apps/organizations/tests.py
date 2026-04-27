from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import SupportStream

from .models import OrgOnboardingState, Organization, OrganizationService

User = get_user_model()


# ---------------------------------------------------------------------------
# Phase 3 helpers
# ---------------------------------------------------------------------------

def _onboarding_org(name="Onboarding Org", status="pending"):
    return Organization.objects.create(
        name=name,
        short_description="Short desc",
        description="Full description",
        status=status,
    )


def _org_manager(org, username="testmanager"):
    user = User.objects.create_user(
        username=username,
        password="testpass",
        role="org_manager",
        organization=org,
    )
    # Tests model approved managers using the portal; registration leaves managers pending.
    user.approval_status = User.APPROVAL_APPROVED
    user.save(update_fields=["approval_status"])
    return user


def _complete_all_steps(state):
    for step, _ in OrgOnboardingState.STEPS:
        state.mark_step_complete(step)


class OrganizationModelTest(TestCase):
    def setUp(self):
        self.stream = SupportStream.objects.create(
            name="Mental Health", display_order=1
        )
        self.org = Organization.objects.create(
            name="Test Organization",
            short_description="A test org",
            description="Full description of test org",
            city="Wolverhampton",
            status="active",
        )
        self.org.support_streams.add(self.stream)

    def test_auto_slug(self):
        self.assertEqual(self.org.slug, "test-organization")

    def test_str(self):
        self.assertEqual(str(self.org), "Test Organization")

    def test_translated_description(self):
        self.org.translated_descriptions = {"pl": "Polska opis"}
        self.org.save()
        self.assertEqual(self.org.get_description_for_language("pl"), "Polska opis")
        self.assertEqual(
            self.org.get_description_for_language("en"),
            "Full description of test org",
        )
        self.assertEqual(
            self.org.get_description_for_language("pa"),
            "Full description of test org",
        )


class OrganizationServiceModelTest(TestCase):
    def setUp(self):
        self.stream = SupportStream.objects.create(
            name="Housing", display_order=1
        )
        self.org = Organization.objects.create(
            name="Test Org",
            short_description="Test",
            description="Test description",
            status="active",
        )
        self.service = OrganizationService.objects.create(
            organization=self.org,
            name="Housing Support",
            description="Help with housing",
            support_stream=self.stream,
            access_model="self_referral",
        )

    def test_str(self):
        self.assertEqual(str(self.service), "Test Org - Housing Support")


class OrganizationListViewTest(TestCase):
    def setUp(self):
        self.stream = SupportStream.objects.create(
            name="Mental Health", display_order=1
        )
        self.active_org = Organization.objects.create(
            name="Active Org",
            short_description="Active",
            description="Active org",
            status="active",
        )
        self.pending_org = Organization.objects.create(
            name="Pending Org",
            short_description="Pending",
            description="Pending org",
            status="pending",
        )

    def test_list_shows_active_only(self):
        response = self.client.get(reverse("organizations:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Org")
        self.assertNotContains(response, "Pending Org")

    def test_filter_by_stream(self):
        self.active_org.support_streams.add(self.stream)
        response = self.client.get(
            reverse("organizations:list") + "?stream=mental-health"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Org")

    def test_list_filters_by_session_postcode(self):
        """With location in session, only orgs with coordinates within radius are listed."""
        self.active_org.city = "Wolverhampton"
        self.active_org.postcode = "WV1 1AA"
        self.active_org.latitude = 52.586
        self.active_org.longitude = -2.129
        self.active_org.save()
        # Far from Wolverhampton (same coords as London approximate)
        other = Organization.objects.create(
            name="Far Away Org",
            short_description="Far",
            description="D",
            status="active",
            latitude=51.50,
            longitude=-0.12,
        )
        s = self.client.session
        s["location_postcode"] = "WV1 1AA"
        s["location_lat"] = 52.586
        s["location_lng"] = -2.129
        s["location_label"] = "Wolverhampton"
        s.save()
        response = self.client.get(reverse("organizations:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Org")
        self.assertNotContains(response, "Far Away Org")
        # sanity: other org is far from target
        self.assertNotIn(other, response.context["organizations"])


class OrganizationDetailViewTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Detail Org",
            short_description="Detail test",
            description="Full description here",
            status="active",
        )

    def test_detail_page_loads(self):
        response = self.client.get(
            reverse("organizations:detail", kwargs={"slug": self.org.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail Org")
        self.assertContains(response, "Full description here")

    def test_detail_404_for_pending(self):
        self.org.status = "pending"
        self.org.save()
        response = self.client.get(
            reverse("organizations:detail", kwargs={"slug": self.org.slug})
        )
        self.assertEqual(response.status_code, 404)


class OrganizationAPITest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="API Org",
            short_description="API test",
            description="API org description",
            status="active",
        )

    def test_api_list(self):
        response = self.client.get("/en/api/v1/organizations/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "API Org")

    def test_api_detail(self):
        response = self.client.get(f"/en/api/v1/organizations/{self.org.slug}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "API Org")


# ===========================================================================
# Phase 3 — Onboarding tests
# ===========================================================================


class OrgOnboardingStateModelTest(TestCase):
    def setUp(self):
        self.org = _onboarding_org()
        self.state = OrgOnboardingState.objects.create(organization=self.org)

    def test_progress_percent_empty(self):
        self.assertEqual(self.state.progress_percent, 0)

    def test_progress_percent_one_step(self):
        self.state.mark_step_complete("about")
        self.assertEqual(self.state.progress_percent, 20)  # 1 of 5

    def test_mark_step_complete_idempotent(self):
        self.state.mark_step_complete("about")
        self.state.mark_step_complete("about")
        self.assertEqual(self.state.completed_steps.count("about"), 1)

    def test_next_incomplete_step_returns_first(self):
        self.assertEqual(self.state.next_incomplete_step(), "about")

    def test_next_incomplete_step_advances(self):
        self.state.mark_step_complete("about")
        self.assertEqual(self.state.next_incomplete_step(), "services")

    def test_next_incomplete_step_none_when_all_done(self):
        _complete_all_steps(self.state)
        self.assertIsNone(self.state.next_incomplete_step())

    def test_is_complete_after_all_steps(self):
        _complete_all_steps(self.state)
        self.state.refresh_from_db()
        self.assertTrue(self.state.is_complete)

    def test_org_onboarding_complete_false_by_default(self):
        self.assertFalse(self.org.onboarding_complete)

    def test_org_onboarding_complete_true_after_all_steps(self):
        _complete_all_steps(self.state)
        self.assertTrue(self.org.onboarding_complete)


class OnboardingWizardAccessTest(TestCase):
    def setUp(self):
        self.org = _onboarding_org()
        self.manager = _org_manager(self.org)

    def test_anonymous_redirected_to_login(self):
        url = reverse("organizations:onboarding")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_user_without_org_redirected(self):
        no_org_user = User.objects.create_user(
            username="noorg", password="pw", role="public"
        )
        self.client.force_login(no_org_user)
        response = self.client.get(reverse("organizations:onboarding"))
        self.assertEqual(response.status_code, 302)

    def test_org_manager_with_org_sees_wizard(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("organizations:onboarding"))
        self.assertEqual(response.status_code, 200)

    def test_wizard_routes_to_about_step_first(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("organizations:onboarding"))
        self.assertTemplateUsed(response, "portal/onboarding/step_about.html")


class OnboardingAboutStepTest(TestCase):
    def setUp(self):
        self.org = _onboarding_org()
        self.manager = _org_manager(self.org)
        self.client.force_login(self.manager)
        self.url = reverse("organizations:onboarding_step", kwargs={"step": "about"})

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portal/onboarding/step_about.html")

    def _about_data(self, **extra):
        data = {
            "name": self.org.name,
            "short_description": "Short desc",
            "description": "Full description",
            "city": "Wolverhampton",
        }
        data.update(extra)
        return data

    def test_post_saves_org_name(self):
        self.client.post(self.url, self._about_data(name="Updated Name"))
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, "Updated Name")

    def test_post_marks_about_complete(self):
        self.client.post(self.url, self._about_data())
        state = OrgOnboardingState.objects.get(organization=self.org)
        self.assertIn("about", state.completed_steps)

    def test_post_redirects_to_services(self):
        response = self.client.post(self.url, self._about_data())
        self.assertRedirects(
            response,
            reverse("organizations:onboarding_step", kwargs={"step": "services"}),
        )


class OnboardingServicesStepTest(TestCase):
    def setUp(self):
        self.org = _onboarding_org()
        self.manager = _org_manager(self.org)
        self.client.force_login(self.manager)
        self.url = reverse("organizations:onboarding_step", kwargs={"step": "services"})

    def _mgmt(self, total=1, initial=0, **extra):
        data = {
            "services-TOTAL_FORMS": str(total),
            "services-INITIAL_FORMS": str(initial),
            "services-MIN_NUM_FORMS": "0",
            "services-MAX_NUM_FORMS": "1000",
        }
        data.update(extra)
        return data

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_empty_formset_marks_step_complete(self):
        self.client.post(self.url, self._mgmt(total=0))
        state = OrgOnboardingState.objects.get(organization=self.org)
        self.assertIn("services", state.completed_steps)

    def test_post_with_service_creates_record(self):
        stream = SupportStream.objects.create(name="Housing", display_order=10)
        self.client.post(self.url, self._mgmt(**{
            "services-0-name": "Housing Help",
            "services-0-description": "Help with housing needs",
            "services-0-access_model": "drop_in",
            "services-0-support_stream": stream.pk,
        }))
        self.assertTrue(
            OrganizationService.objects.filter(
                organization=self.org, name="Housing Help"
            ).exists()
        )


class OnboardingReferralConfigStepTest(TestCase):
    def setUp(self):
        self.org = _onboarding_org()
        self.manager = _org_manager(self.org)
        self.client.force_login(self.manager)
        self.url = reverse("organizations:onboarding_step", kwargs={"step": "referral_config"})

    def _post(self, **extra):
        data = {
            "accepts_referrals": "on",
            "referral_delivery_channels": ["in_platform"],
            "fields-TOTAL_FORMS": "0",
            "fields-INITIAL_FORMS": "0",
            "fields-MIN_NUM_FORMS": "0",
            "fields-MAX_NUM_FORMS": "1000",
        }
        data.update(extra)
        return data

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_marks_step_complete(self):
        self.client.post(self.url, self._post())
        state = OrgOnboardingState.objects.get(organization=self.org)
        self.assertIn("referral_config", state.completed_steps)

    def test_in_platform_always_included(self):
        self.client.post(self.url, self._post(
            **{"referral_delivery_channels": ["email"]}
        ))
        self.org.refresh_from_db()
        self.assertIn("in_platform", self.org.referral_delivery_channels)


class OnboardingScrapingStepTest(TestCase):
    def setUp(self):
        self.org = _onboarding_org()
        self.manager = _org_manager(self.org)
        self.client.force_login(self.manager)
        self.url = reverse("organizations:onboarding_step", kwargs={"step": "scraping"})

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_empty_post_marks_step_complete(self):
        self.client.post(self.url, {})
        state = OrgOnboardingState.objects.get(organization=self.org)
        self.assertIn("scraping", state.completed_steps)

    def test_post_saves_events_url(self):
        self.client.post(self.url, {
            "events_page_url": "https://example.org/events",
        })
        self.org.refresh_from_db()
        self.assertEqual(self.org.events_page_url, "https://example.org/events")


class OnboardingReviewStepTest(TestCase):
    def setUp(self):
        self.org = _onboarding_org()
        self.manager = _org_manager(self.org)
        self.state = OrgOnboardingState.objects.create(organization=self.org)
        self.client.force_login(self.manager)
        self.url = reverse("organizations:onboarding_step", kwargs={"step": "review"})

    def test_get_shows_incomplete_warning(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_publish"])

    def test_get_can_publish_when_all_steps_done(self):
        for step, _ in OrgOnboardingState.STEPS:
            if step != "review":
                self.state.mark_step_complete(step)
        response = self.client.get(self.url)
        self.assertTrue(response.context["can_publish"])

    def test_publish_activates_org(self):
        _complete_all_steps(self.state)
        self.client.post(self.url)
        self.org.refresh_from_db()
        self.assertEqual(self.org.status, "active")

    def test_publish_blocked_when_steps_incomplete(self):
        # POST review without other steps → org stays pending
        self.client.post(self.url)
        self.org.refresh_from_db()
        self.assertNotEqual(self.org.status, "active")


class OnboardingMiddlewareTest(TestCase):
    def setUp(self):
        self.org = _onboarding_org()
        self.manager = _org_manager(self.org)

    def test_incomplete_org_redirected_to_wizard(self):
        # No OrgOnboardingState → org.onboarding_complete is False
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("organizations:portal_dashboard")
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("onboarding", response.url)

    def test_complete_org_passes_through_middleware(self):
        state = OrgOnboardingState.objects.create(organization=self.org)
        _complete_all_steps(state)
        self.client.force_login(self.manager)
        response = self.client.get(
            reverse("organizations:portal_dashboard")
        )
        self.assertEqual(response.status_code, 200)

    def test_onboarding_url_not_intercepted_by_middleware(self):
        # /portal/onboarding/ itself must not be caught by middleware (no redirect loop)
        self.client.force_login(self.manager)
        response = self.client.get(reverse("organizations:onboarding"))
        self.assertEqual(response.status_code, 200)


class PortalDashboardTest(TestCase):
    def setUp(self):
        self.org = _onboarding_org()
        self.manager = _org_manager(self.org)
        self.state = OrgOnboardingState.objects.create(organization=self.org)
        self.url = reverse("organizations:portal_dashboard")

    def test_incomplete_onboarding_redirects_to_wizard(self):
        self.client.force_login(self.manager)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("organizations:onboarding"))

    def test_complete_onboarding_shows_dashboard(self):
        _complete_all_steps(self.state)
        self.client.force_login(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "portal/dashboard.html")

    def test_dashboard_context_has_org(self):
        _complete_all_steps(self.state)
        self.client.force_login(self.manager)
        response = self.client.get(self.url)
        self.assertEqual(response.context["org"], self.org)
