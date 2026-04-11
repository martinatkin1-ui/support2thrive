from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Organization, OrganizationService


class OrganizationServiceInline(admin.TabularInline):
    model = OrganizationService
    extra = 1


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "city", "accepts_referrals", "created_at")
    list_filter = ("status", "city", "accepts_referrals", "support_streams")
    search_fields = ("name", "description", "city")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("areas_served", "tags", "support_streams")
    inlines = [OrganizationServiceInline]

    actions = ["approve_organizations"]

    @admin.action(description=_("Approve selected organizations"))
    def approve_organizations(self, request, queryset):
        queryset.update(status="active")


@admin.register(OrganizationService)
class OrganizationServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "support_stream", "access_model", "is_active")
    list_filter = ("support_stream", "access_model", "is_active")
    search_fields = ("name", "description", "organization__name")
