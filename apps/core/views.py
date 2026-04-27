from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import translation
from django.utils.translation import get_language_from_request
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from .location import (
    clear_session_location,
    geocode_uk_postcode,
    set_session_location,
)
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


def _safe_redirect_path(request) -> str:
    n = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if n and url_has_allowed_host_and_scheme(
        url=n,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return n
    return reverse("core:home")


@require_http_methods(["GET", "POST"])
def set_location(request):
    """
    POST: set session search location (UK postcode). Optionally save to profile if logged in.
    GET: redirect to next or home (for simple links).
    """
    if request.method == "GET":
        return HttpResponseRedirect(_safe_redirect_path(request))

    raw = (request.POST.get("postcode") or "").strip()
    save_profile = request.POST.get("save_to_profile") == "1" and request.user.is_authenticated
    dest = _safe_redirect_path(request)

    if not raw:
        messages.warning(request, _("Please enter a postcode."))
        return HttpResponseRedirect(dest)

    g = geocode_uk_postcode(raw)
    if not g.ok:
        messages.error(
            request,
            _("We could not find that UK postcode. Check the format and try again."),
        )
        return HttpResponseRedirect(dest)

    label = g.admin_district or ""
    set_session_location(
        request,
        postcode=g.postcode,
        lat=g.latitude,
        lng=g.longitude,
        label=label,
    )
    if save_profile:
        u = request.user
        u.home_postcode = g.postcode
        u.home_latitude = g.latitude
        u.home_longitude = g.longitude
        u.home_location_label = label
        u.save(
            update_fields=[
                "home_postcode",
                "home_latitude",
                "home_longitude",
                "home_location_label",
            ]
        )
        messages.success(
            request,
            _("Your home postcode and search area have been saved."),
        )
    else:
        messages.success(
            request,
            _("Search location set. Showing services within about %(miles)s miles of %(pc)s.")
            % {"miles": int(getattr(settings, "LOCATION_SEARCH_RADIUS_MILES", 20)), "pc": g.postcode},
        )
    return HttpResponseRedirect(dest)


@require_http_methods(["POST", "GET"])
def clear_browse_location(request):
    """Clear session override (profile home still applies for logged-in users)."""
    clear_session_location(request)
    messages.info(request, _("Cleared this browser’s search postcode override."))
    return HttpResponseRedirect(_safe_redirect_path(request))
