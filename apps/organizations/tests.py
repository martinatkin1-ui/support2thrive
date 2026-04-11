from django.test import TestCase
from django.urls import reverse

from apps.core.models import SupportStream

from .models import Organization, OrganizationService


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
