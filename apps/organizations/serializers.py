from rest_framework import serializers

from .models import Organization, OrganizationService


class OrganizationServiceSerializer(serializers.ModelSerializer):
    support_stream_name = serializers.CharField(source="support_stream.name", read_only=True)

    class Meta:
        model = OrganizationService
        fields = [
            "id",
            "name",
            "description",
            "support_stream",
            "support_stream_name",
            "access_model",
            "min_age",
            "max_age",
            "eligibility_notes",
            "is_active",
        ]


class OrganizationListSerializer(serializers.ModelSerializer):
    support_streams = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "logo",
            "city",
            "postcode",
            "support_streams",
            "accepts_referrals",
            "accepts_self_referrals",
        ]


class OrganizationDetailSerializer(serializers.ModelSerializer):
    services = OrganizationServiceSerializer(many=True, read_only=True)
    support_streams = serializers.StringRelatedField(many=True, read_only=True)
    areas_served = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "short_description",
            "translated_descriptions",
            "logo",
            "hero_image",
            "website",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "postcode",
            "latitude",
            "longitude",
            "areas_served",
            "support_streams",
            "accepts_referrals",
            "accepts_self_referrals",
            "referral_instructions",
            "opening_hours",
            "services",
            "created_at",
        ]
