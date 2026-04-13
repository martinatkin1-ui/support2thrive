"""
Phase 5 — Pathways: curated support sections for vulnerable population groups.

Content is managed entirely via Django admin. Each Pathway (e.g. "Prison Leavers",
"Homelessness Support") contains ordered Sections, each containing ordered GuideItems.
"""
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import Region, TimeStampedModel


class Pathway(TimeStampedModel):
    """
    Top-level pathway for a specific audience group.
    e.g. "Support for Prison Leavers" or "Homelessness Support".
    """

    AUDIENCE_PRISON_LEAVERS = "prison_leavers"
    AUDIENCE_HOMELESS = "homeless"
    AUDIENCE_BOTH = "both"
    AUDIENCE_CHOICES = [
        (AUDIENCE_PRISON_LEAVERS, _("Prison Leavers")),
        (AUDIENCE_HOMELESS, _("Homelessness")),
        (AUDIENCE_BOTH, _("Both")),
    ]

    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="pathways",
        verbose_name=_("region"),
    )
    title = models.CharField(_("title"), max_length=200)
    slug = models.SlugField(_("slug"), unique=True, max_length=220)
    description = models.TextField(
        _("description"),
        help_text=_("Plain-language introduction shown on the pathway card and hero."),
    )
    icon_name = models.CharField(
        _("icon name"),
        max_length=60,
        default="user-group",
        help_text=_("Heroicons outline icon name, e.g. 'user-group', 'home', 'shield-check'."),
    )
    audience_tag = models.CharField(
        _("audience"),
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default=AUDIENCE_BOTH,
    )
    meta_description = models.CharField(
        _("meta description"),
        max_length=160,
        blank=True,
        default="",
        help_text=_("SEO meta description (max 160 chars)."),
    )
    is_published = models.BooleanField(
        _("published"),
        default=False,
        help_text=_("Only published pathways appear on the public site."),
    )
    display_order = models.PositiveSmallIntegerField(_("display order"), default=0)

    class Meta:
        ordering = ["display_order", "title"]
        verbose_name = _("Pathway")
        verbose_name_plural = _("Pathways")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("pathways:detail", kwargs={"slug": self.slug})


class PathwaySection(TimeStampedModel):
    """
    A grouped content block within a pathway.
    e.g. "First Week", "Housing", "Benefits".
    """

    pathway = models.ForeignKey(
        Pathway,
        on_delete=models.CASCADE,
        related_name="sections",
        verbose_name=_("pathway"),
    )
    title = models.CharField(_("title"), max_length=200)
    body = models.TextField(
        _("body"),
        blank=True,
        default="",
        help_text=_("Introductory text for this section. Plain text."),
    )
    icon_name = models.CharField(
        _("icon name"),
        max_length=60,
        default="information-circle",
        help_text=_("Heroicons outline icon name for this section."),
    )
    display_order = models.PositiveSmallIntegerField(_("display order"), default=0)

    class Meta:
        ordering = ["display_order"]
        verbose_name = _("Pathway Section")
        verbose_name_plural = _("Pathway Sections")

    def __str__(self):
        return f"{self.pathway.title} — {self.title}"


class PathwayGuideItem(TimeStampedModel):
    """
    A single step or checklist item within a section.
    Can optionally link to an organisation, service, or external resource.
    """

    section = models.ForeignKey(
        PathwaySection,
        on_delete=models.CASCADE,
        related_name="guide_items",
        verbose_name=_("section"),
    )
    title = models.CharField(_("title"), max_length=200)
    body = models.TextField(
        _("body"),
        blank=True,
        default="",
        help_text=_("Additional detail or explanation. Plain text."),
    )
    link_url = models.URLField(
        _("link URL"),
        blank=True,
        default="",
        help_text=_("Optional — links to an org profile, external resource, or gov page."),
    )
    link_label = models.CharField(
        _("link label"),
        max_length=100,
        blank=True,
        default="",
        help_text=_("Button label for the link, e.g. 'Find your nearest centre'."),
    )
    is_urgent = models.BooleanField(
        _("urgent"),
        default=False,
        help_text=_("Highlight this item in amber — use for time-critical or emergency steps."),
    )
    display_order = models.PositiveSmallIntegerField(_("display order"), default=0)

    class Meta:
        ordering = ["display_order"]
        verbose_name = _("Guide Item")
        verbose_name_plural = _("Guide Items")

    def __str__(self):
        return f"{self.section} — {self.title}"
