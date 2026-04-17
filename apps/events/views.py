"""
Events views.

Public:
  event_list      /events/             Agenda list + month grid toggle, HTMX navigation
  event_detail    /events/<slug>/      Full event detail
  event_ical      /events/calendar.ics All region events iCal feed
  org_event_ical  /events/org/<slug>/calendar.ics  Per-org iCal feed

Portal (org_manager / admin only):
  portal_event_list    /portal/events/
  portal_event_create  /portal/events/new/
  portal_event_edit    /portal/events/<slug>/edit/
  portal_event_delete  /portal/events/<slug>/delete/
"""

from datetime import date, datetime, timedelta, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.core.models import SupportStream
from apps.organizations.models import Organization

from .forms import EventForm, EventRecurrenceRuleForm
from .ical import build_ical_feed
from .models import Event, EventOccurrence
from .services import generate_occurrences_for_event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_month_bounds(year: int, month: int):
    """Return (first_day, last_day) of the given month."""
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


def _require_org_manager(request, org=None):
    """Return True if request.user can manage events. Raises Http404 otherwise."""
    user = request.user
    if not user.is_authenticated:
        return False
    if user.role == user.ROLE_ADMIN:
        return True
    if user.role == user.ROLE_ORG_MANAGER and user.is_approved:
        if org is None or user.organization == org:
            return True
    return False


# ---------------------------------------------------------------------------
# Public views
# ---------------------------------------------------------------------------

def event_list(request):
    """
    Agenda-first event calendar. Defaults to upcoming 30 days.
    Supports HTMX for date navigation (returns partial if HX-Request header present).
    Toggling to month grid is handled client-side via JS class swap.
    """
    # Date window
    today = date.today()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
    except (ValueError, TypeError):
        year, month = today.year, today.month

    month = max(1, min(12, month))
    first_day, last_day = _get_month_bounds(year, month)

    # Filters
    stream_slug = request.GET.get("stream", "")
    area_slug = request.GET.get("area", "")
    org_slug = request.GET.get("org", "")

    occurrences = (
        EventOccurrence.objects.filter(
            start__date__gte=first_day,
            start__date__lte=last_day,
            is_cancelled=False,
            event__is_published=True,
        )
        .select_related("event", "event__organization", "event__support_stream", "event__region")
        .order_by("start")
    )

    if stream_slug:
        occurrences = occurrences.filter(event__support_stream__slug=stream_slug)
    if area_slug:
        occurrences = occurrences.filter(event__areas__slug=area_slug)
    if org_slug:
        occurrences = occurrences.filter(event__organization__slug=org_slug)

    # Prev / next month navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    support_streams = SupportStream.objects.all()
    context = {
        "occurrences": occurrences,
        "support_streams": support_streams,
        "current_year": year,
        "current_month": month,
        "current_month_label": first_day.strftime("%B %Y"),
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
        "selected_stream": stream_slug,
        "selected_area": area_slug,
        "selected_org": org_slug,
        "today": today,
    }

    if request.htmx:
        return render(request, "public/events/_occurrences.html", context)
    return render(request, "public/events/list.html", context)


def event_detail(request, slug):
    event = get_object_or_404(Event, slug=slug, is_published=True)
    upcoming = (
        event.occurrences.filter(
            start__gte=datetime.now(tz=timezone.utc),
            is_cancelled=False,
        )
        .order_by("start")[:5]
    )
    return render(request, "public/events/detail.html", {
        "event": event,
        "upcoming_occurrences": upcoming,
    })


def event_ical(request):
    """iCal feed for all published events in the current region."""
    occurrences = (
        EventOccurrence.objects.filter(
            event__is_published=True,
            is_cancelled=False,
        )
        .select_related("event", "event__organization")
        .order_by("start")
    )
    cal_bytes = build_ical_feed(occurrences, title="Support2Thrive — All Events")
    return HttpResponse(cal_bytes, content_type="text/calendar; charset=utf-8")


def org_event_ical(request, org_slug):
    """Per-organisation iCal feed."""
    org = get_object_or_404(Organization, slug=org_slug, status="active")
    occurrences = (
        EventOccurrence.objects.filter(
            event__organization=org,
            event__is_published=True,
            is_cancelled=False,
        )
        .select_related("event", "event__organization")
        .order_by("start")
    )
    cal_bytes = build_ical_feed(
        occurrences, title=f"{org.name} — Events"
    )
    return HttpResponse(cal_bytes, content_type="text/calendar; charset=utf-8")


# ---------------------------------------------------------------------------
# Portal views (org manager / admin)
# ---------------------------------------------------------------------------

@login_required
def portal_event_list(request):
    if not _require_org_manager(request):
        raise Http404
    user = request.user
    if user.role == user.ROLE_ADMIN:
        events = Event.objects.select_related("organization", "region").order_by("-created_at")
    else:
        events = Event.objects.filter(
            organization=user.organization
        ).select_related("organization", "region").order_by("-created_at")
    return render(request, "portal/events/list.html", {"events": events})


@login_required
def portal_event_create(request):
    if not _require_org_manager(request):
        raise Http404
    user = request.user

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, user=user)
        rrule_form = EventRecurrenceRuleForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            if user.role != user.ROLE_ADMIN:
                event.organization = user.organization
                event.region = user.organization.region
            event.save()
            form.save_m2m()

            if request.POST.get("is_recurring") and rrule_form.is_valid():
                rr = rrule_form.save(commit=False)
                rr.event = event
                rr.save()

            # Generate occurrences asynchronously (fallback to sync in tests)
            try:
                from .tasks import generate_event_occurrences
                generate_event_occurrences.delay(str(event.pk), replace=True)
            except Exception:
                generate_occurrences_for_event(event, replace=True)

            messages.success(request, _("Event created successfully."))
            return redirect("events:portal_event_list")
    else:
        form = EventForm(user=user)
        rrule_form = EventRecurrenceRuleForm()

    return render(request, "portal/events/form.html", {
        "form": form,
        "rrule_form": rrule_form,
        "action": _("Create Event"),
    })


@login_required
def portal_event_edit(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if not _require_org_manager(request, org=event.organization):
        raise Http404

    rrule_instance = getattr(event, "recurrence_rule", None)

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event, user=request.user)
        rrule_form = EventRecurrenceRuleForm(request.POST, instance=rrule_instance)
        if form.is_valid():
            event = form.save()
            if request.POST.get("is_recurring") and rrule_form.is_valid():
                rr = rrule_form.save(commit=False)
                rr.event = event
                rr.save()
                try:
                    from .tasks import generate_event_occurrences
                    generate_event_occurrences.delay(str(event.pk), replace=True)
                except Exception:
                    generate_occurrences_for_event(event, replace=True)
            messages.success(request, _("Event updated successfully."))
            return redirect("events:portal_event_list")
    else:
        form = EventForm(instance=event, user=request.user)
        rrule_form = EventRecurrenceRuleForm(instance=rrule_instance)

    return render(request, "portal/events/form.html", {
        "form": form,
        "rrule_form": rrule_form,
        "event": event,
        "action": _("Edit Event"),
    })


@login_required
@require_POST
def portal_event_delete(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if not _require_org_manager(request, org=event.organization):
        raise Http404
    title = event.title
    event.delete()
    messages.success(request, _('Event "%(title)s" deleted.') % {"title": title})
    return redirect("events:portal_event_list")
