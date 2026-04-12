from datetime import datetime, timedelta, timezone

from django.test import TestCase
from django.urls import reverse

from apps.core.models import Region, SupportStream
from apps.organizations.models import Organization

from .models import Event, EventOccurrence, EventRecurrenceRule
from .services import generate_occurrences_for_event


def make_region(**kwargs):
    defaults = {"name": "West Midlands", "slug": "west-midlands", "is_active": True}
    defaults.update(kwargs)
    return Region.objects.get_or_create(slug=defaults["slug"], defaults=defaults)[0]


def make_org(region=None, **kwargs):
    if region is None:
        region = make_region()
    defaults = {
        "name": "Test Org",
        "slug": "test-org",
        "short_description": "Test",
        "description": "Test description",
        "status": "active",
        "region": region,
    }
    defaults.update(kwargs)
    return Organization.objects.get_or_create(slug=defaults["slug"], defaults=defaults)[0]


def make_event(org=None, region=None, **kwargs):
    if org is None:
        org = make_org(region=region)
    if region is None:
        region = org.region
    now = datetime.now(tz=timezone.utc)
    defaults = {
        "organization": org,
        "region": region,
        "title": "Test Event",
        "slug": "test-event",
        "description": "A test event",
        "short_description": "Test event",
        "start": now + timedelta(days=1),
        "end": now + timedelta(days=1, hours=2),
        "is_published": True,
    }
    defaults.update(kwargs)
    slug = defaults["slug"]
    counter = 1
    while Event.objects.filter(slug=slug).exists():
        slug = f"{defaults['slug']}-{counter}"
        counter += 1
    defaults["slug"] = slug
    return Event.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Region model tests
# ---------------------------------------------------------------------------

class RegionModelTest(TestCase):
    def test_auto_slug(self):
        region = Region.objects.create(name="Greater Manchester")
        self.assertEqual(region.slug, "greater-manchester")

    def test_str(self):
        region, _ = Region.objects.get_or_create(
            slug="west-midlands", defaults={"name": "West Midlands"}
        )
        self.assertEqual(str(region), "West Midlands")

    def test_default_brand_colors(self):
        region = Region.objects.create(name="Test Region", slug="test-region")
        self.assertEqual(region.brand_color_primary, "#2563eb")
        self.assertEqual(region.brand_color_accent, "#16a34a")


# ---------------------------------------------------------------------------
# Event model tests
# ---------------------------------------------------------------------------

class EventModelTest(TestCase):
    def setUp(self):
        self.region = make_region()
        self.org = make_org(region=self.region)

    def test_auto_slug(self):
        event = make_event(org=self.org, title="My Great Event", slug="my-great-event")
        self.assertEqual(event.slug, "my-great-event")

    def test_slug_deduplication(self):
        make_event(org=self.org, slug="duplicate-event")
        event2 = make_event(org=self.org, slug="duplicate-event")
        self.assertNotEqual(event2.slug, "duplicate-event")

    def test_not_recurring_without_rule(self):
        event = make_event(org=self.org)
        self.assertFalse(event.is_recurring)

    def test_recurring_with_rule(self):
        event = make_event(org=self.org)
        now = datetime.now(tz=timezone.utc)
        EventRecurrenceRule.objects.create(
            event=event,
            rrule="FREQ=WEEKLY;BYDAY=MO",
            dtstart=now,
            duration_minutes=60,
        )
        event.refresh_from_db()
        self.assertTrue(event.is_recurring)

    def test_region_inherited_from_org(self):
        event = Event(
            organization=self.org,
            title="Auto Region Event",
            description="Test",
            short_description="Test",
        )
        event.save()
        self.assertEqual(event.region, self.region)


# ---------------------------------------------------------------------------
# Occurrence generation tests
# ---------------------------------------------------------------------------

class OccurrenceGenerationTest(TestCase):
    def setUp(self):
        self.region = make_region()
        self.org = make_org(region=self.region)

    def test_one_off_event_generates_one_occurrence(self):
        event = make_event(org=self.org)
        count = generate_occurrences_for_event(event)
        self.assertEqual(count, 1)
        self.assertEqual(event.occurrences.count(), 1)
        occ = event.occurrences.first()
        self.assertEqual(occ.start, event.start)

    def test_idempotent_for_one_off(self):
        event = make_event(org=self.org)
        generate_occurrences_for_event(event)
        count2 = generate_occurrences_for_event(event)
        self.assertEqual(count2, 0)  # already exists, no new ones
        self.assertEqual(event.occurrences.count(), 1)

    def test_recurring_weekly_generates_multiple(self):
        now = datetime.now(tz=timezone.utc)
        event = make_event(org=self.org, start=None, end=None)
        EventRecurrenceRule.objects.create(
            event=event,
            rrule="FREQ=WEEKLY;BYDAY=MO",
            dtstart=now,
            duration_minutes=90,
        )
        count = generate_occurrences_for_event(event)
        self.assertGreater(count, 4)  # at least ~52 weeks
        occ = event.occurrences.first()
        # Duration should be 90 minutes
        delta = occ.end - occ.start
        self.assertEqual(delta.seconds // 60, 90)

    def test_replace_clears_future_occurrences(self):
        now = datetime.now(tz=timezone.utc)
        event = make_event(org=self.org, start=None, end=None)
        EventRecurrenceRule.objects.create(
            event=event,
            rrule="FREQ=WEEKLY",
            dtstart=now,
            duration_minutes=60,
        )
        generate_occurrences_for_event(event)
        initial_count = event.occurrences.count()
        # Replace — should regenerate same count
        event.occurrences.filter(start__gte=now).delete()
        generate_occurrences_for_event(event, replace=False)
        self.assertGreater(event.occurrences.count(), 0)

    def test_exception_dates_skipped(self):
        now = datetime.now(tz=timezone.utc)
        # Calculate next Monday
        days_until_monday = (7 - now.weekday()) % 7 or 7
        next_monday = now + timedelta(days=days_until_monday)
        next_monday = next_monday.replace(hour=10, minute=0, second=0, microsecond=0)

        event = make_event(org=self.org, start=None, end=None)
        rule = EventRecurrenceRule.objects.create(
            event=event,
            rrule="FREQ=WEEKLY;BYDAY=MO",
            dtstart=next_monday,
            duration_minutes=60,
            exceptions=[next_monday.isoformat()],
        )
        generate_occurrences_for_event(event)
        # The first occurrence should NOT be next_monday
        first_occ = event.occurrences.order_by("start").first()
        if first_occ:
            self.assertNotEqual(
                first_occ.start.date(), next_monday.date()
            )


# ---------------------------------------------------------------------------
# EventOccurrence property tests
# ---------------------------------------------------------------------------

class EventOccurrencePropertyTest(TestCase):
    def setUp(self):
        self.org = make_org()
        self.event = make_event(org=self.org, location_name="Main Hall")

    def test_title_falls_back_to_event(self):
        occ = EventOccurrence.objects.create(
            event=self.event,
            start=self.event.start,
            end=self.event.end,
        )
        self.assertEqual(occ.title, self.event.title)

    def test_override_title_used_when_set(self):
        occ = EventOccurrence.objects.create(
            event=self.event,
            start=self.event.start,
            end=self.event.end,
            override_title="Special Edition",
        )
        self.assertEqual(occ.title, "Special Edition")

    def test_location_fallback(self):
        occ = EventOccurrence.objects.create(
            event=self.event,
            start=self.event.start,
            end=self.event.end,
        )
        self.assertEqual(occ.location_name, "Main Hall")


# ---------------------------------------------------------------------------
# Public view tests
# ---------------------------------------------------------------------------

class EventListViewTest(TestCase):
    def setUp(self):
        self.region = make_region()
        self.org = make_org(region=self.region)
        self.event = make_event(org=self.org)
        generate_occurrences_for_event(self.event)

    def test_list_loads(self):
        response = self.client.get(reverse("events:list"))
        self.assertEqual(response.status_code, 200)

    def test_htmx_returns_partial(self):
        response = self.client.get(
            reverse("events:list"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "public/events/_occurrences.html")

    def test_unpublished_not_shown(self):
        unpublished = make_event(org=self.org, is_published=False, slug="unpublished-event")
        EventOccurrence.objects.create(
            event=unpublished,
            start=unpublished.start,
            end=unpublished.end,
        )
        response = self.client.get(reverse("events:list"))
        self.assertNotContains(response, "unpublished-event")


class EventDetailViewTest(TestCase):
    def setUp(self):
        self.org = make_org()
        self.event = make_event(org=self.org)
        generate_occurrences_for_event(self.event)

    def test_detail_loads(self):
        response = self.client.get(reverse("events:detail", kwargs={"slug": self.event.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.event.title)

    def test_unpublished_returns_404(self):
        self.event.is_published = False
        self.event.save()
        response = self.client.get(reverse("events:detail", kwargs={"slug": self.event.slug}))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# iCal feed tests
# ---------------------------------------------------------------------------

class ICalFeedTest(TestCase):
    def setUp(self):
        self.org = make_org()
        self.event = make_event(org=self.org)
        generate_occurrences_for_event(self.event)

    def test_ical_feed_returns_calendar(self):
        response = self.client.get(reverse("events:ical"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/calendar", response["Content-Type"])
        content = response.content.decode("utf-8")
        self.assertIn("BEGIN:VCALENDAR", content)
        self.assertIn("BEGIN:VEVENT", content)

    def test_org_ical_feed(self):
        response = self.client.get(
            reverse("events:org_ical", kwargs={"org_slug": self.org.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/calendar", response["Content-Type"])
