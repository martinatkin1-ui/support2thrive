"""
Celery tasks for event occurrence generation and web scraping.
"""
from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_event_occurrences(self, event_id=None, replace=False):
    """
    Generate occurrences for a single event (event_id given) or all published
    events (event_id=None). Called:
    - After an event or recurrence rule is saved (signal)
    - Weekly by Celery beat to extend the rolling 12-month window
    """
    from .models import Event
    from .services import generate_all_occurrences, generate_occurrences_for_event

    try:
        if event_id:
            event = Event.objects.get(pk=event_id)
            count = generate_occurrences_for_event(event, replace=replace)
            return f"Generated {count} occurrences for event {event_id}"
        else:
            count = generate_all_occurrences()
            return f"Generated {count} occurrences platform-wide"
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def scrape_org_events(self, org_id):
    """
    Scrape events from an organisation's events_page_url and create
    draft Event records for manager review. Called weekly by Celery beat.
    """
    import logging

    import requests
    from bs4 import BeautifulSoup
    from django.utils.text import slugify

    from apps.organizations.models import Organization

    logger = logging.getLogger(__name__)

    try:
        org = Organization.objects.get(pk=org_id)
        if not org.events_page_url:
            return f"Org {org_id} has no events_page_url, skipping"

        response = requests.get(org.events_page_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        # Heuristic extraction: find elements that look like event titles
        # Org managers review and publish these drafts.
        candidates = []
        for tag in soup.find_all(["h2", "h3", "h4"], limit=20):
            text = tag.get_text(strip=True)
            if len(text) > 10:
                candidates.append(text)

        from .models import Event

        created = 0
        for title in candidates[:10]:
            slug_base = slugify(title)[:200]
            if not Event.objects.filter(
                organization=org, title=title, is_scraped=True
            ).exists():
                Event.objects.create(
                    organization=org,
                    region=org.region,
                    title=title,
                    slug=slug_base or f"scraped-{org_id}-{created}",
                    description="",
                    short_description=title[:300],
                    is_published=False,
                    is_scraped=True,
                    source_url=org.events_page_url,
                )
                created += 1

        return f"Scraped {created} draft events for org {org_id}"
    except Exception as exc:
        logger.warning("scrape_org_events failed for org %s: %s", org_id, exc)
        raise self.retry(exc=exc)


@shared_task
def scrape_all_org_events():
    """Weekly beat task: scrape events for every org with an events_page_url."""
    from apps.organizations.models import Organization

    org_ids = Organization.objects.filter(
        events_page_url__gt="", status="active"
    ).values_list("id", flat=True)

    for org_id in org_ids:
        scrape_org_events.delay(str(org_id))

    return f"Dispatched scrape tasks for {len(org_ids)} orgs"
