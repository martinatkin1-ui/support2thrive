from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Organization(TimeStampedModel):
    STATUS_CHOICES = [
        ("active", _("Active")),
        ("pending", _("Pending Approval")),
        ("inactive", _("Inactive")),
    ]

    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=255, unique=True)
    description = models.TextField(
        _("description"), help_text=_("Full description of the organization")
    )
    short_description = models.CharField(
        _("short description"), max_length=300, help_text=_("For card/list views")
    )
    translated_descriptions = models.JSONField(
        _("translated descriptions"),
        default=dict,
        blank=True,
        help_text=_('Optional translations: {"pl": "...", "pa": "...", ...}'),
    )
    logo = models.ImageField(
        _("logo"), upload_to="organizations/logos/", blank=True
    )
    hero_image = models.ImageField(
        _("hero image"), upload_to="organizations/heroes/", blank=True
    )
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="pending"
    )

    # Contact
    website = models.URLField(_("website"), blank=True, default="")
    email = models.EmailField(_("email"), blank=True, default="")
    phone = models.CharField(_("phone"), max_length=20, blank=True, default="")
    address_line_1 = models.CharField(
        _("address line 1"), max_length=255, blank=True, default=""
    )
    address_line_2 = models.CharField(
        _("address line 2"), max_length=255, blank=True, default=""
    )
    city = models.CharField(_("city"), max_length=100, default="Wolverhampton")
    postcode = models.CharField(_("postcode"), max_length=10, blank=True, default="")
    latitude = models.DecimalField(
        _("latitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        _("longitude"), max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Taxonomy
    areas_served = models.ManyToManyField(
        "core.GeographicArea", blank=True, verbose_name=_("areas served")
    )
    tags = models.ManyToManyField(
        "core.Tag", blank=True, related_name="organizations", verbose_name=_("tags")
    )
    support_streams = models.ManyToManyField(
        "core.SupportStream",
        blank=True,
        related_name="organizations",
        verbose_name=_("support streams"),
        help_text=_("Which support streams does this organization serve?"),
    )

    # Referral configuration
    accepts_referrals = models.BooleanField(_("accepts referrals"), default=True)
    accepts_self_referrals = models.BooleanField(
        _("accepts self-referrals"), default=True
    )
    referral_email = models.EmailField(
        _("referral email"),
        blank=True,
        default="",
        help_text=_("Email to notify when a referral is received"),
    )
    referral_instructions = models.TextField(
        _("referral instructions"),
        blank=True,
        default="",
        help_text=_("Special instructions for making referrals to this org"),
    )

    # Opening hours
    opening_hours = models.JSONField(
        _("opening hours"),
        default=dict,
        blank=True,
        help_text=_('e.g. {"monday": {"open": "09:00", "close": "17:00"}, ...}'),
    )

    # Website scraping config
    events_page_url = models.URLField(
        _("events page URL"), blank=True, default="",
        help_text=_("URL to scrape for events weekly"),
    )
    news_page_url = models.URLField(
        _("news page URL"), blank=True, default="",
        help_text=_("URL to scrape for news weekly"),
    )

    # RAG indexing
    last_indexed_at = models.DateTimeField(
        _("last indexed"), null=True, blank=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_description_for_language(self, lang_code):
        if lang_code == "en":
            return self.description
        return self.translated_descriptions.get(lang_code, self.description)


class OrganizationService(TimeStampedModel):
    ACCESS_CHOICES = [
        ("drop_in", _("Drop-in")),
        ("self_referral", _("Self-referral")),
        ("professional_referral", _("Professional Referral Required")),
        ("gp_referral", _("GP Referral Required")),
        ("assessment", _("Assessment Required")),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name=_("organization"),
    )
    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"))
    support_stream = models.ForeignKey(
        "core.SupportStream",
        on_delete=models.PROTECT,
        verbose_name=_("support stream"),
    )
    access_model = models.CharField(
        _("access model"),
        max_length=30,
        choices=ACCESS_CHOICES,
        default="self_referral",
    )
    min_age = models.PositiveSmallIntegerField(
        _("minimum age"), null=True, blank=True
    )
    max_age = models.PositiveSmallIntegerField(
        _("maximum age"), null=True, blank=True
    )
    eligibility_notes = models.TextField(
        _("eligibility notes"),
        blank=True,
        default="",
        help_text=_("E.g. 'Must be registered with a Wolverhampton GP'"),
    )
    is_active = models.BooleanField(_("active"), default=True)
    tags = models.ManyToManyField(
        "core.Tag", blank=True, verbose_name=_("tags")
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Organization Service")
        verbose_name_plural = _("Organization Services")

    def __str__(self):
        return f"{self.organization.name} - {self.name}"
