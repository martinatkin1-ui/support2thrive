from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User

from .flickr_feed import sync_community_photos_from_flickr
from .i18n_catalog import collect_all_msgids
from .models import CommunityPhoto, GeographicArea, SiteImage, SupportStream, Tag

# Minimal valid GIF (1x1) for ImageField tests
_MIN_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01"
    b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class RootLanguageRedirectTest(TestCase):
    def test_accept_language_punjabi_redirects_to_pa_prefixed_home(self):
        response = self.client.get("/", HTTP_ACCEPT_LANGUAGE="pa-IN,en;q=0.5")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/pa/"))

    def test_accept_language_fallback_to_english(self):
        response = self.client.get("/", HTTP_ACCEPT_LANGUAGE="de-DE,en;q=0.8")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/en/"))


class I18nCatalogTest(TestCase):
    def test_collect_msgids_non_empty(self):
        msgids = collect_all_msgids()
        self.assertGreater(len(msgids), 50)
        self.assertIn("Login", msgids)


class TagModelTest(TestCase):
    def test_create_tag(self):
        tag = Tag.objects.create(name="Mental Health", category="service_type")
        self.assertEqual(tag.slug, "mental-health")
        self.assertEqual(str(tag), "Mental Health")

    def test_tag_auto_slug(self):
        tag = Tag.objects.create(name="Housing Support", category="service_type")
        self.assertEqual(tag.slug, "housing-support")


class GeographicAreaModelTest(TestCase):
    def test_create_area_with_parent(self):
        wm = GeographicArea.objects.create(name="West Midlands")
        wolv = GeographicArea.objects.create(name="Wolverhampton", parent=wm)
        self.assertEqual(wolv.parent, wm)
        self.assertEqual(str(wolv), "Wolverhampton")
        self.assertIn(wolv, wm.children.all())


class SupportStreamModelTest(TestCase):
    def test_create_support_stream(self):
        stream = SupportStream.objects.create(
            name="Addiction & Recovery",
            description="Substance misuse services",
            display_order=1,
        )
        self.assertEqual(stream.slug, "addiction-recovery")
        self.assertEqual(str(stream), "Addiction & Recovery")


class HomeViewTest(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "West Midlands")

    def test_bundled_fallback_hero_when_no_site_images(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "queens-square-wolverhampton.png")
        self.assertContains(response, "Queen Square")


class SiteImageHeroTest(TestCase):
    def test_reviewed_active_hero_image_on_home(self):
        img = SiteImage.objects.create(
            placement=SiteImage.Placement.HOME_HERO,
            image=ContentFile(_MIN_GIF, name="pixel.gif"),
            alt_text="Approved test image for West Midlands hero",
            credit="Test credit",
            is_active=True,
            reviewed_at=timezone.now(),
        )
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approved test image for West Midlands hero")
        self.assertContains(response, img.image.url)
        self.assertContains(response, "Test credit")

    def test_unreviewed_image_not_shown(self):
        SiteImage.objects.create(
            placement=SiteImage.Placement.HOME_HERO,
            image=ContentFile(_MIN_GIF, name="n.gif"),
            alt_text="Should not appear without review",
            is_active=True,
            reviewed_at=None,
        )
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Should not appear without review")

    def test_inactive_image_not_shown(self):
        SiteImage.objects.create(
            placement=SiteImage.Placement.HOME_HERO,
            image=ContentFile(_MIN_GIF, name="i.gif"),
            alt_text="Inactive hero slot",
            is_active=False,
            reviewed_at=timezone.now(),
        )
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Inactive hero slot")


class AmbientBannerPublicPagesTest(TestCase):
    """Ken Burns ambient strip uses fallback PNG until a placement is curated."""

    def test_organizations_list_includes_ambient_fallback(self):
        response = self.client.get(reverse("organizations:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ambient-page-banner")
        self.assertContains(response, "queens-square-wolverhampton.png")

    def test_events_list_includes_ambient_fallback(self):
        response = self.client.get(reverse("events:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ambient-page-banner")
        self.assertContains(response, "queens-square-wolverhampton.png")

    def test_pathways_list_includes_ambient_fallback(self):
        response = self.client.get(reverse("pathways:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ambient-page-banner")
        self.assertContains(response, "queens-square-wolverhampton.png")

    def test_login_includes_ambient_fallback(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ambient-page-banner")
        self.assertContains(response, "queens-square-wolverhampton.png")

    def test_curated_ambient_overrides_fallback_on_events_list(self):
        img = SiteImage.objects.create(
            placement=SiteImage.Placement.EVENTS_LIST_AMBIENT,
            image=ContentFile(_MIN_GIF, name="events-ambient.gif"),
            alt_text="Curated events list ambient",
            is_active=True,
            reviewed_at=timezone.now(),
            reviewed_by=User.objects.create_user(username="reviewer1", password="x"),
        )
        response = self.client.get(reverse("events:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Curated events list ambient")
        self.assertContains(response, img.image.url)
        self.assertNotContains(response, "queens-square-wolverhampton.png")


class CommunityPhotoSyncTest(TestCase):
    @patch("apps.core.flickr_feed.fetch_flickr_merged")
    def test_sync_upserts_photos(self, mock_merged):
        mock_merged.return_value = (
            [
                {
                    "title": "Canal in the Black Country",
                    "link": "https://www.flickr.com/photos/example/123/",
                    "media": {"m": "https://live.staticflickr.com/65535/123_m.jpg"},
                    "description": "<p>A calm afternoon by the water.</p>",
                    "author": 'nobody@flickr.com ("river-walker")',
                }
            ],
            None,
        )
        processed, err = sync_community_photos_from_flickr(limit=1)
        self.assertIsNone(err)
        self.assertEqual(processed, 1)
        self.assertEqual(CommunityPhoto.objects.count(), 1)
        photo = CommunityPhoto.objects.get()
        self.assertIn("Canal", photo.title)
        self.assertEqual(photo.attribution, "river-walker")
        self.assertTrue(photo.image_url.endswith("_m.jpg"))
