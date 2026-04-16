"""
apps/assistant/rate_limit.py
Phase 6 — Session-based rate limiting for the AI assistant.

Two limits enforced:
  RATE_LIMIT_SESSION_MAX — total messages allowed per session lifecycle
  RATE_LIMIT_MINUTE_MAX  — messages allowed per rolling 60-second window

Thresholds are configurable via Django settings (base.py reads from env vars).
All state stored in request.session — no DB required.
HTMX-safe: check_rate_limit returns (bool, str) so callers return HTTP 200 with error HTML.
"""
from django.conf import settings
from django.utils import timezone

# Read thresholds from settings (set by ASSISTANT_RATE_LIMIT_* env vars)
RATE_LIMIT_SESSION_MAX: int = getattr(settings, "ASSISTANT_RATE_LIMIT_SESSION", 20)
RATE_LIMIT_MINUTE_MAX: int = getattr(settings, "ASSISTANT_RATE_LIMIT_MINUTE", 5)

_WINDOW_SECONDS = 60


def check_rate_limit(request) -> tuple[bool, str]:
    """
    Check and update session-based rate limits.

    Returns (is_allowed, error_message).
    Updates session counters when allowed.
    All state stored in request.session.
    """
    session = request.session

    # Session budget check
    total = session.get("assistant_msg_count", 0)
    if total >= RATE_LIMIT_SESSION_MAX:
        return False, (
            "You've reached the session message limit. "
            "Please start a new session to continue."
        )

    # Per-minute throttle — rolling window
    now = timezone.now().timestamp()
    recent = [
        t for t in session.get("assistant_msg_times", [])
        if now - t < _WINDOW_SECONDS
    ]
    if len(recent) >= RATE_LIMIT_MINUTE_MAX:
        return False, "Please wait a moment before sending another message."

    # Update counters
    recent.append(now)
    session["assistant_msg_count"] = total + 1
    session["assistant_msg_times"] = recent
    session.modified = True

    return True, ""
