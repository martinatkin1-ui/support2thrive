"""Tests for crisis detection module — apps/assistant/crisis.py."""
from django.test import SimpleTestCase


class CrisisDetectionTest(SimpleTestCase):
    """VALIDATION.md: detect_crisis(text) returns True for 15+ crisis keywords; False for safe queries."""

    def setUp(self):
        # crisis.py created in Plan 06-03 — import deferred until then
        # Wave 0: stubs that will pass once crisis.py exists
        pass

    def _detect(self, text: str) -> bool:
        from apps.assistant.crisis import detect_crisis
        return detect_crisis(text)

    # Suicidal ideation
    def test_suicidal_keyword_kill_myself(self):
        self.assertTrue(self._detect("I want to kill myself"))

    def test_suicidal_keyword_end_my_life(self):
        self.assertTrue(self._detect("I want to end my life"))

    def test_suicidal_keyword_suicide(self):
        self.assertTrue(self._detect("I have suicidal thoughts"))

    def test_suicidal_keyword_want_to_die(self):
        self.assertTrue(self._detect("I want to die"))

    def test_suicidal_keyword_no_reason_to_live(self):
        self.assertTrue(self._detect("There's no reason to live anymore"))

    # Self-harm
    def test_self_harm_keyword_hurt_myself(self):
        self.assertTrue(self._detect("I feel like hurting myself"))

    def test_self_harm_keyword_cutting(self):
        self.assertTrue(self._detect("I've been cutting myself"))

    def test_self_harm_keyword_harm_myself(self):
        self.assertTrue(self._detect("urge to harm myself"))

    # Rough sleeping emergency
    def test_rough_sleeping_nowhere_tonight(self):
        self.assertTrue(self._detect("I have nowhere to sleep tonight"))

    def test_rough_sleeping_sleeping_rough(self):
        self.assertTrue(self._detect("I am sleeping rough"))

    def test_rough_sleeping_emergency_housing(self):
        self.assertTrue(self._detect("I need emergency housing now"))

    # Domestic violence
    def test_dv_keyword_being_hit(self):
        self.assertTrue(self._detect("my partner is being hit"))

    def test_dv_keyword_domestic_violence(self):
        self.assertTrue(self._detect("experiencing domestic violence"))

    def test_dv_keyword_unsafe_at_home(self):
        self.assertTrue(self._detect("I feel unsafe at home"))

    def test_dv_keyword_afraid_of_partner(self):
        self.assertTrue(self._detect("afraid of my partner"))

    # Immediate danger
    def test_immediate_danger(self):
        self.assertTrue(self._detect("I am in danger now"))

    # Safe queries — no false positives
    def test_safe_housing_query(self):
        self.assertFalse(self._detect("Can you help me find housing near Birmingham?"))

    def test_safe_food_bank_query(self):
        self.assertFalse(self._detect("Where is the nearest food bank?"))

    def test_safe_prison_leaver_query(self):
        self.assertFalse(self._detect("I just left prison and need support"))

    def test_safe_benefits_query(self):
        self.assertFalse(self._detect("How do I claim Universal Credit?"))
