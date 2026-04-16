import os
import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


def site_image_upload_to(_instance, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()[:10] or ".jpg"
    return f"approved_site/{uuid.uuid4().hex}{ext}"


class Region(models.Model):
    """
    Top-level geographic deployment scope.
    Each Region is an independent instance of the platform (e.g. West Midlands,
    Greater Manchester). All content — organisations, events, referrals — is
    scoped to a Region, enabling white-label multi-region operation from a single
    deployment.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("name"), max_length=100)
    slug = models.SlugField(_("slug"), unique=True)
    description = models.TextField(_("description"), blank=True, default="")
    logo = models.ImageField(
        _("logo"), upload_to="regions/logos/", blank=True
    )
    # Brand colours (hex) — override base Tailwind config per region
    brand_color_primary = models.CharField(
        _("primary colour"), max_length=7, default="#2563eb",
        help_text=_("Hex code e.g. #2563eb"),
    )
    brand_color_accent = models.CharField(
        _("accent colour"), max_length=7, default="#16a34a",
        help_text=_("Hex code e.g. #16a34a"),
    )
    contact_email = models.EmailField(_("contact email"), blank=True, default="")
    website = models.URLField(_("website"), blank=True, default="")
    # Geographic centre for map display
    lat_center = models.DecimalField(
        _("latitude centre"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    lng_center = models.DecimalField(
        _("longitude centre"), max_digits=9, decimal_places=6, null=True, blank=True
    )
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Region")
        verbose_name_plural = _("Regions")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True


class Tag(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("service_type", _("Service Type")),
        ("demographic", _("Demographic")),
        ("access_model", _("Access Model")),
        ("area", _("Geographic Area")),
    ]

    name = models.CharField(_("name"), max_length=100, unique=True)
    slug = models.SlugField(_("slug"), max_length=100, unique=True)
    category = models.CharField(
        _("category"), max_length=50, choices=CATEGORY_CHOICES
    )

    class Meta:
        ordering = ["category", "name"]
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class GeographicArea(TimeStampedModel):
    name = models.CharField(_("name"), max_length=100)
    slug = models.SlugField(_("slug"), unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        verbose_name=_("parent area"),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Geographic Area")
        verbose_name_plural = _("Geographic Areas")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class SupportStream(TimeStampedModel):
    name = models.CharField(_("name"), max_length=100, unique=True)
    slug = models.SlugField(_("slug"), max_length=100, unique=True)
    description = models.TextField(_("description"), blank=True, default="")
    icon = models.CharField(
        _("icon"),
        max_length=50,
        blank=True,
        default="",
        help_text=_("CSS icon class name"),
    )
    display_order = models.PositiveSmallIntegerField(_("display order"), default=0)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = _("Support Stream")
        verbose_name_plural = _("Support Streams")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CommunityPhoto(TimeStampedModel):
    """
    Regional imagery cached from public Flickr feeds (see Real Python Picha pattern).
    Stored locally in the database; image bytes are served by Flickr/CDN.
    """

    title = models.CharField(_("title"), max_length=255)
    source_link = models.URLField(
        _("photo page URL"),
        max_length=512,
        unique=True,
        help_text=_("Link to the Flickr photo page for attribution."),
    )
    image_url = models.URLField(_("image URL"), max_length=512)
    description = models.TextField(_("description"), blank=True, default="")
    attribution = models.CharField(_("attribution"), max_length=255, blank=True, default="")
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        ordering = ["-created_at", "title"]
        verbose_name = _("Community photo")
        verbose_name_plural = _("Community photos")

    def __str__(self):
        return self.title


class SiteImage(TimeStampedModel):
    """
    Staff-curated imagery for platform chrome (hero, banners — not org uploads).
    Only rows with reviewed_at set should appear on public pages.
    """

    class Placement(models.TextChoices):
        HOME_HERO = "home_hero", _("Home hero (full-bleed stack)")
        PATHWAYS_BANNER = "pathways_banner", _("Pathways banner (legacy / future)")
        ORGS_LIST_AMBIENT = "orgs_list_ambient", _("Organisations list — ambient banner")
        ORG_DETAIL_AMBIENT = "org_detail_ambient", _("Organisation detail — ambient banner")
        EVENTS_LIST_AMBIENT = "events_list_ambient", _("Events list — ambient banner")
        EVENT_DETAIL_AMBIENT = "event_detail_ambient", _("Event detail — ambient banner")
        PATHWAYS_LIST_AMBIENT = "pathways_list_ambient", _("Pathways list — ambient banner")
        PATHWAYS_DETAIL_AMBIENT = "pathways_detail_ambient", _("Pathway detail — ambient banner")
        REFERRALS_FORM_AMBIENT = "referrals_form_ambient", _("Referral form — ambient banner")
        REFERRALS_SUBMITTED_AMBIENT = (
            "referrals_submitted_ambient",
            _("Referral submitted — ambient banner"),
        )
        AUTH_SCREENS_AMBIENT = (
            "auth_screens_ambient",
            _("Login / register / profile — ambient banner"),
        )

    placement = models.CharField(
        _("placement"),
        max_length=32,
        choices=Placement.choices,
        default=Placement.HOME_HERO,
        db_index=True,
    )
    image = models.ImageField(_("image"), upload_to=site_image_upload_to)
    alt_text = models.CharField(
        _("alternative text"),
        max_length=255,
        help_text=_("Short description for screen readers (required for accessibility)."),
    )
    caption = models.TextField(_("caption"), blank=True, default="")
    credit = models.CharField(
        _("credit / attribution"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("e.g. Photographer name or licence line, shown on the public site."),
    )
    display_order = models.PositiveSmallIntegerField(_("display order"), default=0)
    is_active = models.BooleanField(_("active"), default=False)
    reviewed_at = models.DateTimeField(_("reviewed at"), null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="site_images_reviewed",
        verbose_name=_("reviewed by"),
    )

    class Meta:
        ordering = ["placement", "display_order", "created_at"]
        verbose_name = _("Site image")
        verbose_name_plural = _("Site images")

    def __str__(self):
        return f"{self.get_placement_display()}: {self.alt_text[:50]}"
