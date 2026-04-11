from django.test import TestCase
from django.urls import reverse

from .models import GeographicArea, SupportStream, Tag


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
