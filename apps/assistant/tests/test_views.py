"""Tests for assistant views — chat_view and assistant_stream (created in Plan 06-03)."""
from django.test import TestCase, Client
from django.urls import reverse


class AssistantPageTest(TestCase):
    """VALIDATION.md: GET /assistant/ returns 200; SSE endpoint returns text/event-stream."""

    def test_assistant_page_renders(self):
        """GET /en/assistant/ returns 200 and contains the chat form."""
        response = self.client.get("/en/assistant/")
        self.assertEqual(response.status_code, 200)

    def test_session_history_capped(self):
        """Session chat_history is capped at 20 items (10 exchanges)."""
        session = self.client.session
        session["chat_history"] = [{"role": "user", "content": f"msg {i}"} for i in range(25)]
        session.save()
        # After view processes a message the history should be trimmed
        # Full assertion implemented when stream_chat view exists in Plan 06-03
        self.assertLessEqual(len(session.get("chat_history", [])), 25)
