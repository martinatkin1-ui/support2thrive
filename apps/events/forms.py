from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Event, EventRecurrenceRule


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title", "short_description", "description", "image",
            "organization", "region",
            "start", "end",
            "location_name", "location_address", "is_online", "online_url",
            "support_stream", "areas", "tags",
            "capacity", "booking_url", "is_free", "cost_description",
            "is_published",
        ]
        widgets = {
            "start": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "end": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "description": forms.Textarea(attrs={"rows": 5}),
            "short_description": forms.Textarea(attrs={"rows": 2}),
            "location_address": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.role != user.ROLE_ADMIN:
            # Org managers can only create events for their own org
            self.fields.pop("organization", None)
            self.fields.pop("region", None)
        self.fields["start"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["end"].input_formats = ["%Y-%m-%dT%H:%M"]
        # Make start/end optional (required for one-off, not for recurring)
        self.fields["start"].required = False
        self.fields["end"].required = False


class EventRecurrenceRuleForm(forms.ModelForm):
    class Meta:
        model = EventRecurrenceRule
        fields = ["rrule", "dtstart", "duration_minutes", "until", "count"]
        widgets = {
            "dtstart": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "until": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "rrule": forms.TextInput(attrs={
                "placeholder": "FREQ=WEEKLY;BYDAY=MO,WE",
                "class": "font-mono",
            }),
        }
        help_texts = {
            "rrule": _("RFC 5545 recurrence rule, e.g. FREQ=WEEKLY;BYDAY=MO or FREQ=MONTHLY;BYMONTHDAY=1"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dtstart"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["until"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["until"].required = False
        self.fields["count"].required = False
