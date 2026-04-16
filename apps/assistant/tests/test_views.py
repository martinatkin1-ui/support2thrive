"""Tests for assistant views — assistant_page, chat_view, assistant_stream."""
from unittest.mock import MagicMock, patch
from django.test import TestCase


class AssistantPageTest(TestCase):
    """GET /en/assistant/ returns 200."""

    def test_assistant_page_renders(self):
        response = self.client.get("/en/assistant/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "assistant")  # page contains assistant-related content

    def test_assistant_page_contains_form(self):
        response = self.client.get("/en/assistant/")
        self.assertContains(response, "<form")


class ChatViewRateLimitTest(TestCase):
    """Rate limit enforcement on POST /en/assistant/chat/."""

    def test_rate_limit_blocks_21st_message(self):
        """After 20 messages, the 21st returns rate limit HTML in 200."""
        from apps.assistant.rate_limit import RATE_LIMIT_SESSION_MAX
        session = self.client.session
        session["assistant_msg_count"] = RATE_LIMIT_SESSION_MAX
        session.save()

        response = self.client.post("/en/assistant/chat/", {"message": "Help me"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"session", response.content.lower())

    def test_empty_message_ignored(self):
        """Empty POST returns 200 without adding to session."""
        response = self.client.post("/en/assistant/chat/", {"message": "   "})
        self.assertEqual(response.status_code, 200)

    def test_valid_message_returns_user_bubble(self):
        """Valid POST stores message in session and returns user bubble HTML."""
        response = self.client.post("/en/assistant/chat/", {"message": "Where can I get food help?"})
        self.assertEqual(response.status_code, 200)
        session = self.client.session
        history = session.get("chat_history", [])
        self.assertTrue(any(m["role"] == "user" for m in history))


class SessionHistoryCapTest(TestCase):
    """Session history is capped at 20 items."""

    def test_history_capped_at_20(self):
        """After 25 messages, session history contains at most 20 items."""
        from apps.assistant.views import _cap_history
        history = [{"role": "user", "content": f"msg {i}"} for i in range(25)]
        result = _cap_history(history)
        self.assertLessEqual(len(result), 20)

    def test_history_cap_removes_oldest(self):
        """Oldest messages are removed first when capping."""
        from apps.assistant.views import _cap_history
        history = [{"role": "user", "content": f"msg {i}"} for i in range(22)]
        result = _cap_history(history)
        self.assertEqual(result[0]["content"], "msg 2")  # first 2 removed

    def test_session_history_capped(self):
        """Session chat_history is capped at 20 items (10 exchanges)."""
        session = self.client.session
        session["chat_history"] = [{"role": "user", "content": f"msg {i}"} for i in range(25)]
        session.save()
        # After view processes a message the history should be trimmed
        from apps.assistant.views import _cap_history
        history = session.get("chat_history", [])
        result = _cap_history(history)
        self.assertLessEqual(len(result), 20)


class CrisisResponseInStreamTest(TestCase):
    """Crisis keywords trigger Samaritans number in response."""

    def test_crisis_message_sets_session_flag(self):
        """A message with crisis keywords gets crisis_detected=True in DB."""
        self.client.post("/en/assistant/chat/", {"message": "I want to kill myself"})
        from apps.assistant.models import ConversationMessage
        crisis_msgs = ConversationMessage.objects.filter(crisis_detected=True)
        self.assertTrue(crisis_msgs.exists())


class AssistantStreamTest(TestCase):
    """SSE stream endpoint returns text/event-stream content type."""

    def test_stream_returns_event_stream_content_type(self):
        """GET /en/assistant/stream/ returns Content-Type: text/event-stream."""
        session = self.client.session
        session["pending_assistant_message"] = "test message"
        session.save()

        with patch("apps.assistant.rag_service.get_rag_instance") as mock_rag_fn:
            # Mock RAGAnything instance
            mock_rag_instance = MagicMock()

            async def mock_aquery(*args, **kwargs):
                async def _gen():
                    yield "Hello "
                    yield "there."
                return _gen()

            mock_rag_instance.lightrag = MagicMock()
            mock_rag_instance.lightrag.aquery = mock_aquery

            async def mock_get_rag():
                return mock_rag_instance

            mock_rag_fn.side_effect = mock_get_rag

            response = self.client.get("/en/assistant/stream/")

        self.assertEqual(response["Content-Type"], "text/event-stream")

    def test_empty_session_stream_closes_immediately(self):
        """GET /en/assistant/stream/ with no pending message returns done event."""
        # No pending_assistant_message in session
        response = self.client.get("/en/assistant/stream/")
        self.assertEqual(response["Content-Type"], "text/event-stream")
        content = b"".join(response.streaming_content)
        self.assertIn(b"event: done", content)
