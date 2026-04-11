from rest_framework import generics

from .models import Organization
from .serializers import OrganizationDetailSerializer, OrganizationListSerializer


class OrganizationListView(generics.ListAPIView):
    serializer_class = OrganizationListSerializer
    filterset_fields = ["status", "city"]
    search_fields = ["name", "description", "short_description"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        return Organization.objects.filter(status="active").prefetch_related(
            "support_streams", "areas_served"
        )


class OrganizationDetailView(generics.RetrieveAPIView):
    serializer_class = OrganizationDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Organization.objects.filter(status="active").prefetch_related(
            "support_streams", "areas_served", "services"
        )
