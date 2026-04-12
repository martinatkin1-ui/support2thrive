"""
iCal feed builder using the icalendar library.
"""
from datetime import timezone

from icalendar import Calendar, Event as ICalEvent, vText


def build_ical_feed(occurrences, title: str = "Events") -> bytes:
    """
    Build an RFC 5545 iCalendar feed from a queryset of EventOccurrence objects.

    Returns UTF-8 encoded bytes ready to serve as text/calendar.
    """
    cal = Calendar()
    cal.add("prodid", "-//WM Community Share//wmcommunityshare.org.uk//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", vText(title))
    cal.add("x-wr-timezone", "Europe/London")

    for occ in occurrences:
        event = occ.event
        ical_event = ICalEvent()
        ical_event.add("uid", f"{occ.pk}@wmcommunityshare.org.uk")
        ical_event.add("summary", occ.title)
        ical_event.add("description", event.description)
        ical_event.add("dtstart", occ.start.astimezone(timezone.utc))
        ical_event.add("dtend", occ.end.astimezone(timezone.utc))

        location_parts = [p for p in [occ.location_name, occ.location_address] if p]
        if location_parts:
            ical_event.add("location", vText(", ".join(location_parts)))

        if event.booking_url:
            ical_event.add("url", event.booking_url)

        organizer_name = event.organization.name
        ical_event.add("organizer", vText(organizer_name))

        if occ.is_cancelled:
            ical_event.add("status", "CANCELLED")

        cal.add_component(ical_event)

    return cal.to_ical()
