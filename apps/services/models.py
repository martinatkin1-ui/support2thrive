
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class ServiceCategory(TimeStampedModel):
    """
    Hierarchical service taxonomy — extends the flat SupportStream list with
    a parent/child tree (e.g. Mental Health → Counselling → Crisis Support).

    Regions can define their own sub-categories beneath the platform-wide roots.
    """

    name = models.CharField(_("name"), max_length=150)
    slug = models.SlugField(_("slug"), max_length=150, unique=True)
    description = models.TextField(_("description"), blank=True, default="")
    icon = models.CharField(
        _("icon"), max_length=50, blank=True, default="",
        help_text=_("CSS/emoji icon identifier for UI display"),
    )
    display_order = models.PositiveSmallIntegerField(_("display order"), default=0)

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("parent category"),
    )
    region = models.ForeignKey(
        "core.Region",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="service_categories",
        verbose_name=_("region"),
        help_text=_("Leave blank for platform-wide categories"),
    )
    # Mirror the legacy SupportStream for backwards compatibility
    support_stream = models.ForeignKey(
        "core.SupportStream",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="categories",
        verbose_name=_("support stream"),
        help_text=_("Optional link to the legacy flat stream"),
    )
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = _("Service Category")
        verbose_name_plural = _("Service Categories")

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} › {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def full_path(self):
        """Return breadcrumb list from root to self."""
        path = [self]
        node = self
        while node.parent_id:
            node = node.parent
            path.insert(0, node)
        return path

    @property
    def depth(self):
        return len(self.full_path) - 1
