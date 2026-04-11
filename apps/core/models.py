import uuid

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


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
