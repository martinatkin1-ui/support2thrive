from django.shortcuts import get_object_or_404, render

from apps.core.models import SupportStream

from .models import Organization


def organization_list(request):
    organizations = Organization.objects.filter(status="active")
    support_streams = SupportStream.objects.all()

    stream_slug = request.GET.get("stream")
    if stream_slug:
        organizations = organizations.filter(support_streams__slug=stream_slug)

    area_slug = request.GET.get("area")
    if area_slug:
        organizations = organizations.filter(areas_served__slug=area_slug)

    organizations = organizations.distinct()

    return render(
        request,
        "public/organizations/list.html",
        {
            "organizations": organizations,
            "support_streams": support_streams,
            "selected_stream": stream_slug,
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
