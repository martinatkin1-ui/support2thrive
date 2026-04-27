from django.conf import settings

from apps.core.location import get_effective_location


def location_context(request):
    loc = get_effective_location(request)
    return {
        "user_location": loc,
        "location_filter_active": loc is not None,
        "location_radius_miles": int(getattr(settings, "LOCATION_SEARCH_RADIUS_MILES", 20)),
    }
