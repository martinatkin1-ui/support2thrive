"""
apps/assistant/crisis.py
Phase 6 — Crisis detection for the AI assistant.

detect_crisis(message) performs substring matching on crisis keywords.
Never refuses to help — crisis detection prepends emergency contacts,
then continues with RAG service information.

Phone numbers marked [VERIFY BEFORE DEPLOY] must be confirmed before launch.
"""

CRISIS_KEYWORDS = {
    "self_harm": [
        "hurt myself", "hurting myself", "self harm", "self-harm", "cutting myself",
        "burn myself", "harm myself",
    ],
    "suicidal": [
        "kill myself", "end my life", "suicide", "suicidal",
        "want to die", "not want to be here", "don't want to live",
        "no reason to live", "take my own life",
    ],
    "rough_sleeping_emergency": [
        "nowhere to sleep tonight", "sleeping outside tonight",
        "no shelter tonight", "rough sleeping", "sleeping rough",
        "emergency housing", "on the streets tonight",
    ],
    "domestic_violence": [
        "being hit", "partner hitting me", "domestic violence",
        "being abused", "afraid of my partner", "unsafe at home",
        "he hits me", "she hits me",
    ],
    "immediate_danger": [
        "in danger now", "being attacked", "help me now",
    ],
}

# Numbers verified [ASSUMED — user must confirm before deployment]
WM_CRISIS_RESPONSE = (
    "**If you're in immediate danger, please call 999 now.**\n\n"
    "**Free 24/7 support:**\n"
    "- Samaritans: **116 123** (free, any time)\n"
    "- Crisis text line: Text SHOUT to **85258**\n"
    "- BVSC Wellbeing (West Midlands): **0800 111 4187**\n\n"
    "**Emergency housing (West Midlands):**\n"
    "- Wolverhampton Housing Advice: **01902 556789** [VERIFY BEFORE DEPLOY]\n"
    "- Birmingham City Council: **0121 303 7410** [VERIFY BEFORE DEPLOY]\n\n"
    "---\n\n"
)


def detect_crisis(message: str) -> bool:
    """
    Returns True if the message contains any crisis keyword.
    Case-insensitive substring match across all crisis categories.
    """
    msg_lower = message.lower()
    for keywords in CRISIS_KEYWORDS.values():
        if any(kw in msg_lower for kw in keywords):
            return True
    return False


def build_crisis_prefix(message: str) -> str:
    """Returns crisis signpost text if crisis detected, else empty string."""
    if detect_crisis(message):
        return WM_CRISIS_RESPONSE
    return ""
