import uuid

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


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
