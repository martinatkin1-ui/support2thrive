"""
Occurrence generation service for recurring and one-off events.

Uses dateutil.rrule (RFC 5545 compatible) to expand recurrence rules into
concrete EventOccurrence rows. A rolling 12-month window is maintained by
the Celery task ``generate_event_occurrences``.
"""
import logging
from datetime import datetime, timedelta, timezone

from dateutil.rrule import rrulestr

from .models import Event, EventOccurrence

logger = logging.getLogger(__name__)


WINDOW_MONTHS = 12  # generate occurrences up to this many months ahead


def _window_end() -> datetime:
    now = datetime.now(tz=timezone.utc)
    # Approximate 12 months = 365 days
    return now + timedelta(days=365 * WINDOW_MONTHS // 12)


def generate_occurrences_for_event(event: Event, replace: bool = False) -> int:
    """
    Generate EventOccurrence rows for *event* within the rolling window.

    For one-off events: creates exactly one occurrence from event.start/end.
    For recurring events: expands the rrule up to WINDOW_MONTHS ahead,
    skipping exception dates.

    Args:
        event: The Event instance to generate occurrences for.
        replace: If True, delete all existing future occurrences first
                 (used when the rrule is edited).

    Returns:
        Number of occurrences created.
    """
    now = datetime.now(tz=timezone.utc)
    window_end = _window_end()

    if replace:
        event.occurrences.filter(start__gte=now).delete()

    if not event.is_recurring:
        # One-off event — single occurrence mirroring event.start/end
        if not event.start:
            return 0
        _, created = EventOccurrence.objects.get_or_create(
            event=event,
            start=event.start,
            defaults={"end": event.end or event.start + timedelta(hours=1)},
        )
        return 1 if created else 0

    rule = event.recurrence_rule
    exception_dts = set()
    for exc in rule.exceptions:
        try:
            dt = datetime.fromisoformat(exc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            exception_dts.add(dt)
        except (ValueError, TypeError):
            pass

    # Build the rrule string with dtstart for dateutil
    full_rule = f"DTSTART:{rule.dtstart.strftime('%Y%m%dT%H%M%SZ')}\nRRULE:{rule.rrule}"
    if rule.until:
        # Honour the explicit until date if it's sooner than our window
        until = min(rule.until, window_end)
        full_rule += f";UNTIL={until.strftime('%Y%m%dT%H%M%SZ')}"
    if rule.count:
        full_rule += f";COUNT={rule.count}"

    try:
        rule_iter = rrulestr(full_rule, ignoretz=False)
    except (ValueError, TypeError) as exc:
        logger.warning("generate_occurrences_for_event: invalid rrule for event %s: %s", event.pk, exc)
        return 0

    duration = timedelta(minutes=rule.duration_minutes)
    created_count = 0

    for occ_start in rule_iter:
        if occ_start.tzinfo is None:
            occ_start = occ_start.replace(tzinfo=timezone.utc)

        # Stop once we're past the generation window
        if occ_start > window_end:
            break
        # Skip exception dates
        if occ_start in exception_dts:
            continue

        occ_end = occ_start + duration
        _, created = EventOccurrence.objects.get_or_create(
            event=event,
            start=occ_start,
            defaults={"end": occ_end},
        )
        if created:
            created_count += 1

    return created_count


def generate_occurrences_for_region(region_id) -> int:
    """Generate/refresh occurrences for all published events in a region."""
    total = 0
    events = Event.objects.filter(region_id=region_id, is_published=True)
    for event in events:
        total += generate_occurrences_for_event(event)
    return total


def generate_all_occurrences() -> int:
    """Generate/refresh occurrences for every published event platform-wide."""
    total = 0
    for event in Event.objects.filter(is_published=True):
        total += generate_occurrences_for_event(event)
    return total
