from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import ServiceCategory


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "region", "display_order", "is_active"]
    list_filter = ["is_active", "region", "parent"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["display_order", "name"]
    fieldsets = [
        (None, {"fields": ["name", "slug", "description", "icon", "display_order", "is_active"]}),
        (_("Hierarchy"), {"fields": ["parent", "region", "support_stream"]}),
    ]
