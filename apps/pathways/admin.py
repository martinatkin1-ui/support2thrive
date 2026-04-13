from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Pathway, PathwayGuideItem, PathwaySection


class PathwayGuideItemInline(admin.TabularInline):
    model = PathwayGuideItem
    extra = 1
    fields = ("title", "body", "link_url", "link_label", "is_urgent", "display_order")


class PathwaySectionInline(admin.StackedInline):
    model = PathwaySection
    extra = 1
    fields = ("title", "body", "icon_name", "display_order")
    show_change_link = True


@admin.register(PathwaySection)
class PathwaySectionAdmin(admin.ModelAdmin):
    list_display = ("title", "pathway", "display_order")
    list_filter = ("pathway",)
    ordering = ("pathway", "display_order")
    inlines = [PathwayGuideItemInline]


@admin.register(Pathway)
class PathwayAdmin(admin.ModelAdmin):
    list_display = ("title", "audience_tag", "region", "is_published", "display_order")
    list_filter = ("is_published", "audience_tag", "region")
    list_editable = ("is_published", "display_order")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "description")
    ordering = ("display_order", "title")
    inlines = [PathwaySectionInline]
    fieldsets = (
        (None, {
            "fields": ("region", "title", "slug", "audience_tag", "is_published", "display_order"),
        }),
        (_("Content"), {
            "fields": ("description", "icon_name", "meta_description"),
        }),
    )
