from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Event, EventOccurrence, EventRecurrenceRule


class EventRecurrenceRuleInline(admin.StackedInline):
    model = EventRecurrenceRule
    extra = 0
    fields = ("rrule", "dtstart", "duration_minutes", "until", "count", "exceptions")


class EventOccurrenceInline(admin.TabularInline):
    model = EventOccurrence
    extra = 0
    fields = ("start", "end", "is_cancelled", "override_title", "override_location_name")
    readonly_fields = ("start", "end")
    ordering = ("start",)
    max_num = 20


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title", "organization", "region", "support_stream",
        "start", "is_recurring_display", "is_published", "is_scraped",
    )
    list_filter = ("is_published", "is_scraped", "is_free", "is_online", "region", "support_stream")
    search_fields = ("title", "organization__name", "location_name")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("is_scraped", "source_url")
    inlines = [EventRecurrenceRuleInline, EventOccurrenceInline]
    fieldsets = (
        (None, {
            "fields": ("organization", "region", "title", "slug", "short_description", "description", "image"),
        }),
        (_("Date & Time"), {
            "fields": ("start", "end"),
            "description": _("For one-off events only. Recurring events use the Recurrence Rule inline below."),
        }),
        (_("Location"), {
            "fields": ("location_name", "location_address", "is_online", "online_url", "latitude", "longitude"),
        }),
        (_("Taxonomy"), {
            "fields": ("support_stream", "areas", "tags"),
        }),
        (_("Booking"), {
            "fields": ("capacity", "booking_url", "is_free", "cost_description"),
        }),
        (_("Publishing"), {
            "fields": ("is_published",),
        }),
        (_("Scraping"), {
            "fields": ("is_scraped", "source_url"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(boolean=True, description=_("Recurring"))
    def is_recurring_display(self, obj):
        return obj.is_recurring


@admin.register(EventOccurrence)
class EventOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("event", "start", "end", "is_cancelled")
    list_filter = ("is_cancelled", "event__region")
    search_fields = ("event__title",)
    date_hierarchy = "start"
    ordering = ("start",)
