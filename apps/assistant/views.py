"""
apps/assistant/views.py
Phase 6 — AI Assistant views.

Stub implementation for Wave 0. Full chat views (SSE streaming, rate limiting,
crisis detection) implemented in Plan 06-03.
"""
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


def assistant_page(request):
    """Stub landing page for the AI assistant — expanded in Plan 06-03."""
    return render(request, "assistant/chat.html", {
        "page_title": _("Community Assistant"),
    })
