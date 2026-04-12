from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Referral, ReferralDelivery, ReferralFormField, ReferralStatusHistory


class ReferralFormFieldInline(admin.TabularInline):
    model = ReferralFormField
    extra = 0
    fields = ["label", "field_type", "is_required", "display_order", "is_active"]
    ordering = ["display_order"]


class ReferralDeliveryInline(admin.TabularInline):
    model = ReferralDelivery
    extra = 0
    readonly_fields = ["channel", "status", "attempts", "last_attempted_at", "error_log"]
    can_delete = False


class ReferralStatusHistoryInline(admin.TabularInline):
    model = ReferralStatusHistory
    extra = 0
    readonly_fields = ["from_status", "to_status", "changed_by", "changed_at", "note"]
    can_delete = False


@admin.register(ReferralFormField)
class ReferralFormFieldAdmin(admin.ModelAdmin):
    list_display = ["organization", "label", "field_type", "is_required", "display_order", "is_active"]
    list_filter = ["organization", "field_type", "is_required", "is_active"]
    search_fields = ["label", "organization__name"]
    ordering = ["organization", "display_order"]


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        "reference_number", "organization", "status", "priority",
        "consent_given", "acknowledged_at", "escalated", "created_at",
    ]
    list_filter = ["status", "priority", "escalated", "organization"]
    search_fields = ["reference_number", "organization__name"]
    readonly_fields = [
        "reference_number", "encrypted_pii", "created_at", "updated_at",
        "acknowledged_at", "acknowledged_by", "consent_timestamp",
    ]
    date_hierarchy = "created_at"
    inlines = [ReferralDeliveryInline, ReferralStatusHistoryInline]
    fieldsets = [
        (None, {
            "fields": [
                "reference_number", "organization", "referring_user", "referring_org",
                "status", "priority", "escalated",
            ]
        }),
        (_("Form data"), {"fields": ["form_data", "encrypted_pii"]}),
        (_("Consent"), {"fields": ["consent_given", "consent_timestamp", "consent_statement"]}),
        (_("Acknowledgment"), {"fields": ["acknowledged_at", "acknowledged_by"]}),
        (_("Notes"), {"fields": ["notes"]}),
    ]

    def has_change_permission(self, request, obj=None):
        # Referrals should only be updated via the status transition flow
        return request.user.is_superuser


@admin.register(ReferralDelivery)
class ReferralDeliveryAdmin(admin.ModelAdmin):
    list_display = ["referral", "channel", "status", "attempts", "last_attempted_at"]
    list_filter = ["channel", "status"]
    readonly_fields = ["referral", "channel", "attempts", "last_attempted_at", "error_log"]
