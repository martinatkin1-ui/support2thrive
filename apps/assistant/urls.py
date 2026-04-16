"""URL configuration for the AI assistant app."""
from django.urls import path

from apps.assistant import views

app_name = "assistant"

urlpatterns = [
    path("", views.assistant_page, name="page"),
    path("chat/", views.chat_view, name="chat"),
    path("stream/", views.assistant_stream, name="stream"),
]
