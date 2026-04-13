"""
Onboarding wizard forms — one form per step.
"""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.models import GeographicArea, SupportStream
from apps.referrals.models import ReferralFormField
from apps.services.models import ServiceCategory

from .models import Organization, OrganizationService


# ---------------------------------------------------------------------------
# Step 1 — About
# ---------------------------------------------------------------------------

class OnboardingAboutForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "name", "short_description", "description",
            "logo", "hero_image",
            "website", "email", "phone",
            "address_line_1", "address_line_2", "city", "postcode",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "short_description": forms.Textarea(attrs={"rows": 2}),
        }


# ---------------------------------------------------------------------------
# Step 2 — Services
# ---------------------------------------------------------------------------

class OrganizationServiceForm(forms.ModelForm):
    class Meta:
        model = OrganizationService
        fields = [
            "name", "description", "support_stream", "category",
            "access_model", "min_age", "max_age", "eligibility_notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "eligibility_notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ServiceCategory.objects.filter(is_active=True)
        self.fields["category"].required = False


class OnboardingSupportStreamsForm(forms.ModelForm):
    """Select which support streams (top-level) the org covers."""
    class Meta:
        model = Organization
        fields = ["support_streams", "areas_served"]
        widgets = {
            "support_streams": forms.CheckboxSelectMultiple,
            "areas_served": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["support_streams"].queryset = SupportStream.objects.all()
        self.fields["areas_served"].queryset = GeographicArea.objects.all()
        self.fields["support_streams"].required = False
        self.fields["areas_served"].required = False


# ---------------------------------------------------------------------------
# Step 3 — Referral Config
# ---------------------------------------------------------------------------

DELIVERY_CHANNEL_CHOICES = [
    ("in_platform", _("In-platform inbox (always enabled)")),
    ("email", _("Email to referral email address")),
    ("csv", _("CSV download from portal")),
    ("print", _("Print-ready view (paper filing)")),
    ("crm_webhook", _("CRM webhook (outbound JSON)")),
]


class OnboardingReferralConfigForm(forms.ModelForm):
    referral_delivery_channels = forms.MultipleChoiceField(
        choices=DELIVERY_CHANNEL_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label=_("Delivery channels"),
        help_text=_("How should referrals reach you? In-platform is always active."),
        initial=["in_platform"],
        required=False,
    )

    class Meta:
        model = Organization
        fields = [
            "accepts_referrals", "accepts_self_referrals",
            "referral_email", "referral_instructions",
            "referral_delivery_channels",
            "crm_webhook_url", "crm_webhook_secret",
        ]
        widgets = {
            "referral_instructions": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill channels from the org instance
        instance = kwargs.get("instance")
        if instance and instance.referral_delivery_channels:
            self.initial["referral_delivery_channels"] = instance.referral_delivery_channels

    def clean_referral_delivery_channels(self):
        channels = self.cleaned_data.get("referral_delivery_channels", [])
        # in_platform is always included
        if "in_platform" not in channels:
            channels = ["in_platform"] + list(channels)
        return channels


class ReferralFormFieldForm(forms.ModelForm):
    class Meta:
        model = ReferralFormField
        fields = [
            "label", "field_type", "help_text", "placeholder",
            "is_required", "options", "display_order",
        ]
        widgets = {
            "help_text": forms.TextInput,
            "placeholder": forms.TextInput,
        }


# ---------------------------------------------------------------------------
# Step 4 — Scraping Config
# ---------------------------------------------------------------------------

class OnboardingScrapingForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["events_page_url", "news_page_url"]
        help_texts = {
            "events_page_url": _(
                "URL of a page listing your events. We'll scrape it weekly "
                "and add draft events for your review."
            ),
            "news_page_url": _(
                "URL of your news/blog page. We'll scrape it weekly."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["events_page_url"].required = False
        self.fields["news_page_url"].required = False
