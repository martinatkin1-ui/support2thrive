from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    CommunityPhoto,
    GeographicArea,
    Region,
    SiteImage,
    SupportStream,
    Tag,
)


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


@admin.register(CommunityPhoto)
class CommunityPhotoAdmin(admin.ModelAdmin):
    list_display = ("title", "attribution", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "attribution", "source_link")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SiteImage)
class SiteImageAdmin(admin.ModelAdmin):
    list_display = (
        "alt_text",
        "placement",
        "display_order",
        "is_active",
        "reviewed_at",
        "created_at",
    )
    list_filter = ("placement", "is_active")
    search_fields = ("alt_text", "caption", "credit")
    list_editable = ("display_order", "is_active")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            _("Image"),
            {"fields": ("placement", "image", "alt_text", "caption", "credit")},
        ),
        (
            _("Publishing"),
            {"fields": ("display_order", "is_active")},
        ),
        (
            _("Review"),
            {
                "fields": ("reviewed_at", "reviewed_by"),
                "description": _(
                    "Public pages only show images that are active and have a "
                    "review timestamp. Use this to record human moderation."
                ),
            },
        ),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )
