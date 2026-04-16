"""
apps/assistant/urls.py
Phase 6 — AI Assistant URL configuration.

Stub routes for Wave 0. Full routes (SSE stream, etc.) added in Plan 06-03.
"""
from django.urls import path
from . import views

app_name = "assistant"

urlpatterns = [
    path("", views.assistant_page, name="chat"),
]
