"""Tests for rate_limit module — apps/assistant/rate_limit.py (created in Plan 06-03)."""
from django.test import TestCase, RequestFactory
from django.contrib.sessions.backends.db import SessionStore


class RateLimitTest(TestCase):
    """VALIDATION.md: 21st message returns rate limit error; 6th message in 60s throttled."""

    def _make_request_with_session(self):
        factory = RequestFactory()
        request = factory.get("/assistant/")
        request.session = SessionStore()
        request.session.create()
        return request

    def test_first_message_allowed(self):
        from apps.assistant.rate_limit import check_rate_limit
        request = self._make_request_with_session()
        allowed, msg = check_rate_limit(request)
        self.assertTrue(allowed)
        self.assertEqual(msg, "")

    def test_20th_message_allowed(self):
        from apps.assistant.rate_limit import check_rate_limit, RATE_LIMIT_SESSION_MAX
        request = self._make_request_with_session()
        request.session["assistant_msg_count"] = RATE_LIMIT_SESSION_MAX - 1
        allowed, msg = check_rate_limit(request)
        self.assertTrue(allowed)

    def test_21st_message_blocked(self):
        from apps.assistant.rate_limit import check_rate_limit, RATE_LIMIT_SESSION_MAX
        request = self._make_request_with_session()
        request.session["assistant_msg_count"] = RATE_LIMIT_SESSION_MAX
        allowed, msg = check_rate_limit(request)
        self.assertFalse(allowed)
        self.assertIn("session", msg.lower())

    def test_per_minute_throttle_6th_message_blocked(self):
        from apps.assistant.rate_limit import check_rate_limit, RATE_LIMIT_MINUTE_MAX
        from django.utils import timezone
        request = self._make_request_with_session()
        now = timezone.now().timestamp()
        request.session["assistant_msg_times"] = [now - i for i in range(RATE_LIMIT_MINUTE_MAX)]
        allowed, msg = check_rate_limit(request)
        self.assertFalse(allowed)
        self.assertIn("moment", msg.lower())

    def test_old_timestamps_not_counted(self):
        """Timestamps older than 60 seconds do not count toward per-minute limit."""
        from apps.assistant.rate_limit import check_rate_limit, RATE_LIMIT_MINUTE_MAX
        from django.utils import timezone
        request = self._make_request_with_session()
        old_time = timezone.now().timestamp() - 120
        request.session["assistant_msg_times"] = [old_time] * (RATE_LIMIT_MINUTE_MAX + 5)
        allowed, _ = check_rate_limit(request)
        self.assertTrue(allowed)
