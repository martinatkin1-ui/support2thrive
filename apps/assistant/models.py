"""
apps/assistant/models.py
Phase 6 — AI Assistant models.

Models:
  AssistantQuery    — lightweight log of queries/responses (no PII stored)
  OrgDocument       — org-uploaded PDFs, indexed into LightRAG
  Conversation      — ties a chat session to a Django session key
  ConversationMessage — individual messages within a conversation
"""
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class AssistantQuery(models.Model):
    """
    Lightweight log of assistant queries.
    DO NOT store PII (names, addresses, DOB) in query_text or response_text.
    These fields are for performance monitoring and debugging only.
    """
    session_key = models.CharField(
        _("session key"), max_length=40, db_index=True
    )
    query_text = models.TextField(_("query text"), max_length=500)
    response_text = models.TextField(_("response text"), blank=True, default="")
    sources = models.JSONField(_("sources"), null=True, blank=True)
    response_time_ms = models.PositiveIntegerField(
        _("response time (ms)"), null=True, blank=True
    )
    created_at = models.DateTimeField(_("created"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Assistant Query")
        verbose_name_plural = _("Assistant Queries")

    def __str__(self):
        return f"Query {self.session_key[:8]}\u2026 ({self.created_at:%Y-%m-%d})"


class Conversation(models.Model):
    """
    Ties a chat session to a Django session key.
    Created on first message; no login required.
    Used for admin visibility and rate-limit counting.
    """
    session_key = models.CharField(
        _("session key"), max_length=40, db_index=True, unique=True
    )
    created_at = models.DateTimeField(_("created"), auto_now_add=True)
    last_active = models.DateTimeField(_("last active"), auto_now=True)

    class Meta:
        ordering = ["-last_active"]
        verbose_name = _("Conversation")
        verbose_name_plural = _("Conversations")

    def __str__(self):
        return f"Conversation {self.session_key[:8]}\u2026"


class ConversationMessage(models.Model):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_CHOICES = [
        (ROLE_USER, _("User")),
        (ROLE_ASSISTANT, _("Assistant")),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("conversation"),
    )
    role = models.CharField(_("role"), max_length=10, choices=ROLE_CHOICES)
    content = models.TextField(_("content"))
    sources = models.JSONField(
        _("sources"),
        null=True,
        blank=True,
        help_text=_('List of {"name": "...", "url": "..."} dicts'),
    )
    crisis_detected = models.BooleanField(_("crisis detected"), default=False)
    created_at = models.DateTimeField(_("created"), auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Conversation Message")
        verbose_name_plural = _("Conversation Messages")

    def __str__(self):
        return f"{self.role}: {self.content[:50]}\u2026"


def org_doc_upload_path(instance, filename):
    return f"org_documents/{instance.org.slug}/{filename}"


class OrgDocument(TimeStampedModel):
    """
    Org-uploaded PDFs — parsed by pymupdf4llm and indexed into LightRAG.
    Size limit (20MB) enforced at form level in forms.py.
    Extension limit (.pdf only) enforced by FileExtensionValidator.
    """
    org = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("organisation"),
    )
    title = models.CharField(_("title"), max_length=255)
    file = models.FileField(
        _("file"),
        upload_to=org_doc_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("uploaded by"),
    )
    indexed_at = models.DateTimeField(_("indexed at"), null=True, blank=True)
    index_error = models.TextField(_("index error"), blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Org Document")
        verbose_name_plural = _("Org Documents")

    def __str__(self):
        return f"{self.org.name} \u2014 {self.title}"
