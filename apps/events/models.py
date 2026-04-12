import uuid

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import GeographicArea, Region, SupportStream, Tag, TimeStampedModel


class Event(TimeStampedModel):
    """
    Master event record owned by an organisation.

    Single (non-recurring) events have no EventRecurrenceRule. Recurring events
    have exactly one EventRecurrenceRule and one or more pre-generated
    EventOccurrence rows for the rolling 12-month window.

    Scalability: scoped to a Region so the same deployment serves multiple
    geographic areas without data bleed.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=_("organisation"),
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name=_("region"),
    )
    title = models.CharField(_("title"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255, unique=True)
    description = models.TextField(_("description"))
    short_description = models.CharField(
        _("short description"), max_length=300,
        help_text=_("Displayed on event cards and list views"),
    )

    # Location
    location_name = models.CharField(_("location name"), max_length=255, blank=True, default="")
    location_address = models.TextField(_("location address"), blank=True, default="")
    is_online = models.BooleanField(_("online event"), default=False)
    online_url = models.URLField(_("online URL"), blank=True, default="")
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("longitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Taxonomy
    support_stream = models.ForeignKey(
        SupportStream,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
        verbose_name=_("support stream"),
    )
    areas = models.ManyToManyField(
        GeographicArea, blank=True, verbose_name=_("areas"),
        help_text=_("Geographic areas this event is relevant to"),
    )
    tags = models.ManyToManyField(Tag, blank=True, verbose_name=_("tags"))

    # Media
    image = models.ImageField(_("image"), upload_to="events/images/", blank=True)

    # Booking / capacity
    capacity = models.PositiveIntegerField(_("capacity"), null=True, blank=True)
    booking_url = models.URLField(_("booking URL"), blank=True, default="")
    is_free = models.BooleanField(_("free event"), default=True)
    cost_description = models.CharField(
        _("cost description"), max_length=100, blank=True, default="",
        help_text=_('e.g. "£5 suggested donation"'),
    )

    # For non-recurring events: explicit start/end stored here.
    # For recurring events: start/end are on each EventOccurrence.
    start = models.DateTimeField(_("start"), null=True, blank=True)
    end = models.DateTimeField(_("end"), null=True, blank=True)

    # Publishing
    is_published = models.BooleanField(_("published"), default=False)

    # Scraping provenance
    source_url = models.URLField(_("source URL"), blank=True, default="")
    is_scraped = models.BooleanField(_("scraped"), default=False)

    class Meta:
        ordering = ["start"]
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        indexes = [
            models.Index(fields=["region", "is_published", "start"]),
            models.Index(fields=["organization", "is_published"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_recurring(self):
        return hasattr(self, "recurrence_rule")

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            n = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        # Inherit region from organisation if not set
        if not self.region_id and self.organization_id:
            self.region = self.organization.region
        super().save(*args, **kwargs)


class EventRecurrenceRule(TimeStampedModel):
    """
    RFC 5545 recurrence rule for a repeating event.

    Stores the RRULE string (e.g. ``FREQ=WEEKLY;BYDAY=MO,WE``) parsed by
    ``dateutil.rrule``. A separate Celery task pre-generates EventOccurrence
    rows for the rolling 12-month window whenever this rule changes.
    """

    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name="recurrence_rule",
        verbose_name=_("event"),
    )
    # RFC 5545 RRULE string without the "RRULE:" prefix
    rrule = models.TextField(
        _("rrule"),
        help_text=_(
            "RFC 5545 recurrence rule, e.g. FREQ=WEEKLY;BYDAY=MO or FREQ=MONTHLY;BYMONTHDAY=1"
        ),
    )
    dtstart = models.DateTimeField(_("first occurrence start"))
    duration_minutes = models.PositiveIntegerField(
        _("duration (minutes)"), default=60,
        help_text=_("Applied to every generated occurrence"),
    )
    # Optional hard end
    until = models.DateTimeField(_("repeat until"), null=True, blank=True)
    count = models.PositiveIntegerField(
        _("max occurrences"), null=True, blank=True,
        help_text=_("Leave blank for indefinite recurrence"),
    )
    # ISO datetime strings of cancelled/skipped dates
    exceptions = models.JSONField(
        _("exception dates"), default=list, blank=True,
        help_text=_("List of ISO-8601 datetimes excluded from the recurrence"),
    )

    class Meta:
        verbose_name = _("Recurrence Rule")
        verbose_name_plural = _("Recurrence Rules")

    def __str__(self):
        return f"{self.event.title} — {self.rrule}"


class EventOccurrence(TimeStampedModel):
    """
    A single generated occurrence of a recurring (or one-off) event.

    One-off events have exactly one occurrence mirroring Event.start/end.
    Recurring events have occurrences pre-generated by the Celery task
    ``generate_event_occurrences`` for a rolling 12-month window.

    Per-occurrence overrides (e.g. a one-off venue change) are stored as
    override_* fields; empty string / null means "use the parent event value".
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="occurrences",
        verbose_name=_("event"),
    )
    start = models.DateTimeField(_("start"), db_index=True)
    end = models.DateTimeField(_("end"))
    is_cancelled = models.BooleanField(_("cancelled"), default=False)

    # Per-occurrence overrides
    override_title = models.CharField(_("override title"), max_length=255, blank=True, default="")
    override_description = models.TextField(_("override description"), blank=True, default="")
    override_location_name = models.CharField(
        _("override location name"), max_length=255, blank=True, default=""
    )
    override_location_address = models.TextField(
        _("override location address"), blank=True, default=""
    )

    class Meta:
        ordering = ["start"]
        verbose_name = _("Event Occurrence")
        verbose_name_plural = _("Event Occurrences")
        indexes = [
            models.Index(fields=["event", "start"]),
            models.Index(fields=["start", "end", "is_cancelled"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "start"], name="unique_event_occurrence"
            )
        ]

    def __str__(self):
        return f"{self.event.title} @ {self.start:%Y-%m-%d %H:%M}"

    @property
    def title(self):
        return self.override_title or self.event.title

    @property
    def location_name(self):
        return self.override_location_name or self.event.location_name

    @property
    def location_address(self):
        return self.override_location_address or self.event.location_address
