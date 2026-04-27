from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "get_full_name",
        "role",
        "organization",
        "approval_status",
        "is_active",
    )
    list_filter = ("role", "approval_status", "is_active", "organization")
    search_fields = ("username", "email", "first_name", "last_name")

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            _("Platform"),
            {
                "fields": (
                    "role",
                    "phone",
                    "organization",
                    "approval_status",
                    "approved_by",
                    "approved_at",
                    "preferred_language",
                    "last_active",
                ),
            },
        ),
        (
            _("Search location"),
            {
                "fields": (
                    "home_postcode",
                    "home_location_label",
                    "home_latitude",
                    "home_longitude",
                ),
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            _("Platform"),
            {
                "fields": ("role", "organization", "preferred_language"),
            },
        ),
    )

    actions = ["approve_users", "reject_users"]

    @admin.action(description=_("Approve selected users"))
    def approve_users(self, request, queryset):
        from django.utils import timezone

        queryset.update(
            approval_status=User.APPROVAL_APPROVED,
            approved_by=request.user,
            approved_at=timezone.now(),
        )

    @admin.action(description=_("Reject selected users"))
    def reject_users(self, request, queryset):
        queryset.update(approval_status=User.APPROVAL_REJECTED)
