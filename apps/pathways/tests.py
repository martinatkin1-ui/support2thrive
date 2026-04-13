from django.test import TestCase
from django.urls import reverse

from apps.core.models import Region
from apps.pathways.models import Pathway, PathwayGuideItem, PathwaySection


def _make_region():
    return Region.objects.get_or_create(
        slug="west-midlands",
        defaults={"name": "West Midlands"},
    )[0]


def _make_pathway(region, published=True, **kwargs):
    defaults = {
        "title": "Test Pathway",
        "slug": "test-pathway",
        "description": "A test pathway.",
        "is_published": published,
        "display_order": 1,
    }
    defaults.update(kwargs)
    return Pathway.objects.create(region=region, **defaults)


def _make_section(pathway, **kwargs):
    defaults = {"title": "Test Section", "display_order": 1}
    defaults.update(kwargs)
    return PathwaySection.objects.create(pathway=pathway, **defaults)


def _make_item(section, **kwargs):
    defaults = {"title": "Test Item", "display_order": 1}
    defaults.update(kwargs)
    return PathwayGuideItem.objects.create(section=section, **defaults)


class PathwayModelTests(TestCase):
    def setUp(self):
        self.region = _make_region()

    def test_pathway_str(self):
        pathway = _make_pathway(self.region)
        self.assertEqual(str(pathway), "Test Pathway")

    def test_pathway_slug_auto_set(self):
        pathway = Pathway(
            region=self.region,
            title="My New Pathway",
            description="desc",
        )
        pathway.save()
        self.assertEqual(pathway.slug, "my-new-pathway")

    def test_pathway_get_absolute_url(self):
        pathway = _make_pathway(self.region)
        self.assertIn("test-pathway", pathway.get_absolute_url())

    def test_section_str(self):
        pathway = _make_pathway(self.region)
        section = _make_section(pathway, title="Housing")
        self.assertIn("Test Pathway", str(section))
        self.assertIn("Housing", str(section))

    def test_guide_item_str(self):
        pathway = _make_pathway(self.region)
        section = _make_section(pathway)
        item = _make_item(section, title="Register with GP")
        self.assertIn("Register with GP", str(item))


class PathwayListViewTests(TestCase):
    def setUp(self):
        self.region = _make_region()
        self.url = reverse("pathways:list")

    def test_empty_list_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_published_pathway_appears(self):
        _make_pathway(self.region, title="Prison Leavers")
        response = self.client.get(self.url)
        self.assertContains(response, "Prison Leavers")

    def test_unpublished_pathway_hidden(self):
        _make_pathway(self.region, title="Hidden Pathway", slug="hidden", published=False)
        response = self.client.get(self.url)
        self.assertNotContains(response, "Hidden Pathway")

    def test_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "public/pathways/list.html")


class PathwayDetailViewTests(TestCase):
    def setUp(self):
        self.region = _make_region()
        self.pathway = _make_pathway(self.region)
        self.url = reverse("pathways:detail", kwargs={"slug": self.pathway.slug})

    def test_published_pathway_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_unpublished_pathway_returns_404(self):
        unpublished = _make_pathway(
            self.region, title="Unpublished", slug="unpublished", published=False
        )
        url = reverse("pathways:detail", kwargs={"slug": unpublished.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_pathway_returns_404(self):
        response = self.client.get(reverse("pathways:detail", kwargs={"slug": "does-not-exist"}))
        self.assertEqual(response.status_code, 404)

    def test_sections_and_items_rendered(self):
        section = _make_section(self.pathway, title="First Week")
        _make_item(section, title="Contact probation officer")
        response = self.client.get(self.url)
        self.assertContains(response, "First Week")
        self.assertContains(response, "Contact probation officer")

    def test_urgent_item_shows_important_badge(self):
        section = _make_section(self.pathway)
        _make_item(section, title="Urgent Step", is_urgent=True)
        response = self.client.get(self.url)
        self.assertContains(response, "Important")

    def test_uses_correct_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "public/pathways/detail.html")

    def test_item_with_link_renders_link(self):
        section = _make_section(self.pathway)
        _make_item(
            section,
            title="Shelter link",
            link_url="https://shelter.org.uk",
            link_label="Visit Shelter",
        )
        response = self.client.get(self.url)
        self.assertContains(response, "Visit Shelter")
        self.assertContains(response, "https://shelter.org.uk")


class PathwayAdminTests(TestCase):
    def test_pathway_registered_in_admin(self):
        from django.contrib.admin.sites import AdminSite
        from apps.pathways.admin import PathwayAdmin
        site = AdminSite()
        admin_instance = PathwayAdmin(Pathway, site)
        self.assertEqual(admin_instance.model, Pathway)
