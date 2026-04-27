from django.db.models import Case, IntegerField, Value, When

from rest_framework import generics

from apps.core.location import (
    filter_organizations_by_distance,
    geocode_uk_postcode,
)

from .models import Organization
from .serializers import OrganizationDetailSerializer, OrganizationListSerializer


class OrganizationListView(generics.ListAPIView):
    serializer_class = OrganizationListSerializer
    filterset_fields = ["status", "city"]
    search_fields = ["name", "description", "short_description"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        qs = Organization.objects.filter(status="active").prefetch_related(
            "support_streams", "areas_served"
        )
        near = (self.request.query_params.get("near_postcode") or "").strip()
        if not near:
            return qs
        g = geocode_uk_postcode(near)
        if not g.ok:
            return Organization.objects.none()
        ordered = filter_organizations_by_distance(
            qs, g.latitude, g.longitude
        )
        pks = [o.pk for o in ordered]
        if not pks:
            return Organization.objects.none()
        whens = [When(pk=pk, then=Value(i)) for i, pk in enumerate(pks)]
        preserved = Case(*whens, output_field=IntegerField())
        return (
            Organization.objects.filter(pk__in=pks, status="active")
            .prefetch_related("support_streams", "areas_served")
            .order_by(preserved)
        )


class OrganizationDetailView(generics.RetrieveAPIView):
    serializer_class = OrganizationDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Organization.objects.filter(status="active").prefetch_related(
            "support_streams", "areas_served", "services"
        )
