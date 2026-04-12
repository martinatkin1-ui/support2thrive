from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import GeographicArea, Region, SupportStream, Tag


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "contact_email")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "logo", "is_active")}),
        (_("Branding"), {"fields": ("brand_color_primary", "brand_color_accent")}),
        (_("Contact"), {"fields": ("contact_email", "website")}),
        (_("Geography"), {"fields": ("lat_center", "lng_center")}),
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug")
    list_filter = ("category",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GeographicArea)
class GeographicAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(SupportStream)
class SupportStreamAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("display_order",)
