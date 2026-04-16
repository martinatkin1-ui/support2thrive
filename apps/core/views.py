from pathlib import Path

from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import get_language_from_request

from .models import CommunityPhoto, SiteImage, SupportStream


def root_language_redirect(request):
    """
    Map bare `/` to the localized home URL using the same negotiation as
    LocaleMiddleware (session / cookie / Accept-Language), so phones set to
    e.g. Punjabi get `pa` without manually using the language switcher.
    """
    lang = get_language_from_request(request, check_path=False)
    translation.activate(lang)
    return redirect(reverse("core:home"))


# Bundled hero when no curated SiteImage rows (e.g. Flickr sync unavailable).
_FALLBACK_HERO_STATIC = "site/hero/queens-square-wolverhampton.png"
_FALLBACK_HERO_FILE = (
    Path(settings.BASE_DIR) / "static" / "site" / "hero" / "queens-square-wolverhampton.png"
)


def home(request):
    support_streams = SupportStream.objects.all()
    hero_max = int(getattr(settings, "SITE_IMAGE_HERO_MAX", 3))
    site_hero_images = list(
        SiteImage.objects.filter(
            placement=SiteImage.Placement.HOME_HERO,
            is_active=True,
            reviewed_at__isnull=False,
        ).order_by("display_order", "created_at")[:hero_max]
    )
    hero_credits = " · ".join(
        img.credit.strip() for img in site_hero_images if (img.credit or "").strip()
    )

    fallback_static_hero = (
        _FALLBACK_HERO_STATIC if _FALLBACK_HERO_FILE.is_file() else None
    )
    hero_has_immersive_bg = bool(site_hero_images) or bool(fallback_static_hero)

    community_photos = []
    if getattr(settings, "HERO_USE_FLICKR_COMMUNITY_PHOTOS", False):
        hero_n = int(getattr(settings, "COMMUNITY_PHOTO_HERO_DISPLAY", 6))
        community_photos = list(
            CommunityPhoto.objects.filter(is_active=True).order_by("-created_at")[
                :hero_n
            ]
        )

    return render(request, "public/home.html", {
        "support_stream_names": [s.name for s in support_streams],
        "site_hero_images": site_hero_images,
        "hero_credits": hero_credits,
        "fallback_static_hero": fallback_static_hero,
        "hero_has_immersive_bg": hero_has_immersive_bg,
        "community_photos": community_photos,
    })
