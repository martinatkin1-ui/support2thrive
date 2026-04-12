from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import AuditEntry


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "action", "actor_email", "object_id", "entry_hash_short"]
    list_filter = ["action"]
    search_fields = ["actor_email", "action", "object_id"]
    readonly_fields = [
        "id", "actor", "actor_email", "action", "content_type", "object_id",
        "delta", "metadata", "timestamp", "prev_hash", "entry_hash",
    ]
    date_hierarchy = "timestamp"

    def entry_hash_short(self, obj):
        return obj.entry_hash[:12] + "…"
    entry_hash_short.short_description = _("Hash")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
