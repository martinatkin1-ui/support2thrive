"""
apps/assistant/admin.py
Django admin for the AI Assistant app.

Provides:
  OrgDocumentAdmin  — org document management with indexing status display
  OrgDocumentInline — inline on OrganizationAdmin to manage docs from org detail page
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.assistant.models import AssistantQuery, Conversation, OrgDocument


class OrgDocumentInline(admin.TabularInline):
    model = OrgDocument
    extra = 0
    fields = ["title", "file", "indexed_at", "index_error"]
    readonly_fields = ["indexed_at", "index_error"]
    can_delete = True
    verbose_name = _("Org Document")
    verbose_name_plural = _("Org Documents (AI Indexing)")


@admin.register(OrgDocument)
class OrgDocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "org", "uploaded_by", "indexed_status", "created_at"]
    list_filter = ["org", "indexed_at"]
    search_fields = ["title", "org__name"]
    readonly_fields = ["indexed_at", "index_error", "created_at", "updated_at"]
    raw_id_fields = ["org", "uploaded_by"]
    fieldsets = [
        (None, {"fields": ["org", "title", "file", "uploaded_by"]}),
        (_("Indexing Status"), {"fields": ["indexed_at", "index_error"], "classes": ["collapse"]}),
        (_("Timestamps"), {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]

    @admin.display(description=_("Indexed"), boolean=True)
    def indexed_status(self, obj):
        return obj.indexed_at is not None and not obj.index_error


@admin.register(AssistantQuery)
class AssistantQueryAdmin(admin.ModelAdmin):
    list_display = ["session_key", "query_text_truncated", "response_time_ms", "created_at"]
    list_filter = ["created_at"]
    readonly_fields = ["session_key", "query_text", "response_text", "sources", "response_time_ms", "created_at"]

    def has_add_permission(self, request):
        return False

    @admin.display(description=_("Query"))
    def query_text_truncated(self, obj):
        return obj.query_text[:80] + "\u2026" if len(obj.query_text) > 80 else obj.query_text


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["session_key", "created_at", "last_active"]
    readonly_fields = ["session_key", "created_at", "last_active"]

    def has_add_permission(self, request):
        return False
