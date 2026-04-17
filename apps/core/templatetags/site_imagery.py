"""Template tags for staff-curated site imagery."""

from pathlib import Path

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.translation import gettext as _

from apps.core.models import SiteImage

register = template.Library()

_FALLBACK_STATIC = "site/hero/queens-square-wolverhampton.png"


@register.inclusion_tag("public/_ambient_banner.html")
def ambient_banner(placement: str):
    """
    Curated image for a page placement, else the bundled regional fallback.
    Only reviewed, active SiteImage rows are used (same rules as home hero).
    """
    valid = {c.value for c in SiteImage.Placement}
    if placement not in valid:
        return {"image_url": None, "alt_text": "", "credit": ""}

    img = (
        SiteImage.objects.filter(
            placement=placement,
            is_active=True,
            reviewed_at__isnull=False,
        )
        .order_by("display_order", "created_at")
        .first()
    )
    if img:
        return {
            "image_url": img.image.url,
            "alt_text": img.alt_text,
            "credit": img.credit or "",
        }

    fallback = Path(settings.BASE_DIR) / "static" / _FALLBACK_STATIC
    if fallback.is_file():
        return {
            "image_url": static(_FALLBACK_STATIC),
            "alt_text": _("West Midlands city scene — Queen Square, Wolverhampton"),
            "credit": "",
        }
    return {"image_url": None, "alt_text": "", "credit": ""}
