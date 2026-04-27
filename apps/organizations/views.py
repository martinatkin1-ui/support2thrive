from django.conf import settings
from django.shortcuts import get_object_or_404, render

from apps.core.location import (
    filter_organizations_by_distance,
    get_effective_location,
)
from apps.core.models import SupportStream

from .models import Organization


def organization_list(request):
    organizations = (
        Organization.objects.filter(status="active")
        .select_related("region")
        .prefetch_related("support_streams", "tags")
    )
    support_streams = SupportStream.objects.all()

    stream_slug = request.GET.get("stream")
    if stream_slug:
        organizations = organizations.filter(support_streams__slug=stream_slug)

    area_slug = request.GET.get("area")
    if area_slug:
        organizations = organizations.filter(areas_served__slug=area_slug)

    organizations = organizations.distinct()
    loc = get_effective_location(request)
    radius = float(
        getattr(settings, "LOCATION_SEARCH_RADIUS_MILES", 20)
    )
    if loc:
        organizations = filter_organizations_by_distance(
            organizations, loc["lat"], loc["lng"], radius
        )
    else:
        organizations = list(organizations)

    return render(
        request,
        "public/organizations/list.html",
        {
            "organizations": organizations,
            "support_streams": support_streams,
            "selected_stream": stream_slug,
            "search_location": loc,
            "location_radius_miles": int(radius),
        },
    )


def organization_detail(request, slug):
    organization = get_object_or_404(Organization, slug=slug, status="active")
    services = organization.services.filter(is_active=True)
    return render(
        request,
        "public/organizations/detail.html",
        {
            "organization": organization,
            "services": services,
        },
    )
