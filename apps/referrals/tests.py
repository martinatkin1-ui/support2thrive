"""
Tests for Phase 3/4: ServiceCategory, OrgOnboardingState, Referral system,
encryption, delivery, and audit chain.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Region
from apps.organizations.models import OrgOnboardingState, Organization
from apps.services.models import ServiceCategory

from .encryption import decrypt_pii, encrypt_pii
from .models import Referral, ReferralDelivery, ReferralFormField, ReferralStatusHistory
from .services import create_referral, queue_deliveries

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_region(**kwargs):
    defaults = {"name": "West Midlands", "slug": "west-midlands", "is_active": True}
    defaults.update(kwargs)
    return Region.objects.get_or_create(slug=defaults["slug"], defaults=defaults)[0]


def make_org(region=None, **kwargs):
    if region is None:
        region = make_region()
    defaults = {
        "name": "Test Org",
        "slug": "test-org-referrals",
        "short_description": "Test",
        "description": "Test description",
        "status": "active",
        "region": region,
        "accepts_referrals": True,
        "referral_email": "referrals@testorg.example.com",
        "referral_delivery_channels": ["in_platform", "email"],
    }
    defaults.update(kwargs)
    return Organization.objects.get_or_create(slug=defaults["slug"], defaults=defaults)[0]


def make_user(role="volunteer", **kwargs):
    defaults = {
        "username": f"user_{role}",
        "email": f"{role}@example.com",
        "password": "testpass123",
        "role": role,
        "approval_status": "approved",
    }
    defaults.update(kwargs)
    return User.objects.get_or_create(
        username=defaults["username"],
        defaults=defaults,
    )[0]


# ---------------------------------------------------------------------------
# ServiceCategory tests
# ---------------------------------------------------------------------------

class ServiceCategoryTest(TestCase):
    def test_str_root(self):
        cat = ServiceCategory.objects.create(name="Mental Health", slug="mental-health")
        self.assertEqual(str(cat), "Mental Health")

    def test_str_child(self):
        parent = ServiceCategory.objects.create(name="Mental Health", slug="mental-health-2")
        child = ServiceCategory.objects.create(
            name="Counselling", slug="counselling", parent=parent
        )
        self.assertIn("Mental Health", str(child))
        self.assertIn("Counselling", str(child))

    def test_auto_slug(self):
        cat = ServiceCategory(name="Housing Support")
        cat.save()
        self.assertEqual(cat.slug, "housing-support")

    def test_full_path(self):
        grandparent = ServiceCategory.objects.create(name="Health", slug="health")
        parent = ServiceCategory.objects.create(name="Mental Health", slug="mh", parent=grandparent)
        child = ServiceCategory.objects.create(name="CBT", slug="cbt", parent=parent)
        path = child.full_path
        self.assertEqual(len(path), 3)
        self.assertEqual(path[0], grandparent)
        self.assertEqual(path[2], child)

    def test_depth(self):
        root = ServiceCategory.objects.create(name="Root", slug="root")
        child = ServiceCategory.objects.create(name="Child", slug="child", parent=root)
        self.assertEqual(root.depth, 0)
        self.assertEqual(child.depth, 1)


# ---------------------------------------------------------------------------
# OrgOnboardingState tests
# ---------------------------------------------------------------------------

class OrgOnboardingStateTest(TestCase):
    def setUp(self):
        self.org = make_org()
        self.state, _ = OrgOnboardingState.objects.get_or_create(organization=self.org)

    def test_initial_state(self):
        self.assertFalse(self.state.is_complete)
        self.assertEqual(self.state.completed_steps, [])
        self.assertEqual(self.state.progress_percent, 0)

    def test_mark_step_complete(self):
        self.state.mark_step_complete("about")
        self.assertIn("about", self.state.completed_steps)
        self.assertFalse(self.state.is_complete)

    def test_idempotent_step_marking(self):
        self.state.mark_step_complete("about")
        self.state.mark_step_complete("about")
        self.assertEqual(self.state.completed_steps.count("about"), 1)

    def test_complete_when_all_steps_done(self):
        for step, _ in OrgOnboardingState.STEPS:
            self.state.mark_step_complete(step)
        self.state.refresh_from_db()
        self.assertTrue(self.state.is_complete)
        self.assertIsNotNone(self.state.completed_at)

    def test_progress_percent(self):
        all_steps = [s for s, _ in OrgOnboardingState.STEPS]
        self.state.mark_step_complete(all_steps[0])
        expected = int(1 / len(all_steps) * 100)
        self.assertEqual(self.state.progress_percent, expected)

    def test_next_incomplete_step(self):
        self.state.mark_step_complete("about")
        next_step = self.state.next_incomplete_step()
        self.assertEqual(next_step, "services")

    def test_next_incomplete_step_none_when_all_done(self):
        for step, _ in OrgOnboardingState.STEPS:
            self.state.mark_step_complete(step)
        self.assertIsNone(self.state.next_incomplete_step())

    def test_org_onboarding_complete_property(self):
        self.assertFalse(self.org.onboarding_complete)
        for step, _ in OrgOnboardingState.STEPS:
            self.state.mark_step_complete(step)
        self.assertTrue(self.org.onboarding_complete)


# ---------------------------------------------------------------------------
# Encryption tests
# ---------------------------------------------------------------------------

class EncryptionTest(TestCase):
    def test_round_trip(self):
        data = {"name": "Jane Doe", "dob": "1985-03-15", "nhs_number": "123 456 7890"}
        token = encrypt_pii(data)
        self.assertIsInstance(token, str)
        self.assertNotEqual(token, "")
        recovered = decrypt_pii(token)
        self.assertEqual(recovered, data)

    def test_empty_dict_returns_empty_string(self):
        self.assertEqual(encrypt_pii({}), "")

    def test_empty_token_returns_empty_dict(self):
        self.assertEqual(decrypt_pii(""), {})

    def test_invalid_token_returns_empty_dict(self):
        self.assertEqual(decrypt_pii("not-a-valid-token"), {})

    def test_unicode_pii(self):
        data = {"name": "محمد", "address": "123 الشارع الرئيسي"}
        token = encrypt_pii(data)
        recovered = decrypt_pii(token)
        self.assertEqual(recovered["name"], "محمد")


# ---------------------------------------------------------------------------
# ReferralFormField tests
# ---------------------------------------------------------------------------

class ReferralFormFieldTest(TestCase):
    def setUp(self):
        self.org = make_org()

    def test_pii_field_types(self):
        pii_field = ReferralFormField.objects.create(
            organization=self.org, field_type="nhs_number", label="NHS Number",
        )
        non_pii_field = ReferralFormField.objects.create(
            organization=self.org, field_type="select", label="Preferred contact method",
        )
        self.assertTrue(pii_field.is_pii)
        self.assertFalse(non_pii_field.is_pii)

    def test_slug_from_label(self):
        field = ReferralFormField(
            organization=self.org, field_type="text", label="Full Name",
        )
        self.assertEqual(field.slug, "full_name")


# ---------------------------------------------------------------------------
# Referral creation and delivery tests
# ---------------------------------------------------------------------------

class ReferralCreationTest(TestCase):
    def setUp(self):
        self.org = make_org()
        self.user = make_user()

    def test_create_referral_stores_pii_encrypted(self):
        pii = {"name": "Jane Doe", "dob": "1990-01-01", "consent": True}
        referral = create_referral(
            org=self.org,
            form_data={"priority": "normal"},
            pii_dict=pii,
            referring_user=self.user,
        )
        self.assertIsNotNone(referral.pk)
        self.assertTrue(referral.encrypted_pii)
        # Raw stored value should not contain plaintext name
        self.assertNotIn("Jane Doe", referral.encrypted_pii)
        # Decrypted value should match
        recovered = referral.get_pii()
        self.assertEqual(recovered.get("name"), "Jane Doe")

    def test_create_referral_consent_recorded(self):
        referral = create_referral(
            org=self.org,
            form_data={},
            pii_dict={"consent": True},
            referring_user=self.user,
        )
        self.assertTrue(referral.consent_given)
        self.assertIsNotNone(referral.consent_timestamp)

    def test_create_referral_no_consent(self):
        referral = create_referral(
            org=self.org,
            form_data={},
            pii_dict={"consent": False},
        )
        self.assertFalse(referral.consent_given)

    def test_reference_number_format(self):
        referral = create_referral(org=self.org, form_data={}, pii_dict={"consent": True})
        self.assertTrue(referral.reference_number.startswith("WM-"))

    def test_unique_reference_numbers(self):
        refs = set()
        for _ in range(5):
            r = create_referral(org=self.org, form_data={}, pii_dict={"consent": True})
            refs.add(r.reference_number)
        self.assertEqual(len(refs), 5)


class ReferralDeliveryTest(TestCase):
    def setUp(self):
        self.org = make_org(referral_delivery_channels=["in_platform"])

    def test_in_platform_delivery_always_sent(self):
        referral = create_referral(org=self.org, form_data={}, pii_dict={"consent": True})
        deliveries = queue_deliveries(referral)
        in_platform = next((d for d in deliveries if d.channel == "in_platform"), None)
        self.assertIsNotNone(in_platform)
        self.assertEqual(in_platform.status, "sent")

    def test_unique_delivery_per_channel(self):
        referral = create_referral(org=self.org, form_data={}, pii_dict={"consent": True})
        queue_deliveries(referral)
        queue_deliveries(referral)  # second call should not duplicate
        count = ReferralDelivery.objects.filter(referral=referral, channel="in_platform").count()
        self.assertEqual(count, 1)


# ---------------------------------------------------------------------------
# Referral status transition tests
# ---------------------------------------------------------------------------

class ReferralStatusTest(TestCase):
    def setUp(self):
        self.org = make_org()
        self.user = make_user(role="org_manager", username="mgr", email="mgr@example.com")
        self.referral = create_referral(
            org=self.org, form_data={}, pii_dict={"consent": True}
        )

    def test_initial_status(self):
        self.assertEqual(self.referral.status, "submitted")

    def test_transition_to_acknowledged(self):
        self.referral.transition_status("acknowledged", actor=self.user)
        self.referral.refresh_from_db()
        self.assertEqual(self.referral.status, "acknowledged")
        self.assertIsNotNone(self.referral.acknowledged_at)
        self.assertEqual(self.referral.acknowledged_by, self.user)

    def test_history_recorded(self):
        self.referral.transition_status("acknowledged", actor=self.user, note="Portal")
        history = ReferralStatusHistory.objects.filter(referral=self.referral)
        self.assertEqual(history.count(), 1)
        h = history.first()
        self.assertEqual(h.from_status, "submitted")
        self.assertEqual(h.to_status, "acknowledged")
        self.assertEqual(h.note, "Portal")


# ---------------------------------------------------------------------------
# Audit chain tests
# ---------------------------------------------------------------------------

class AuditChainTest(TestCase):
    def test_log_creates_entry(self):
        from apps.audit.models import AuditEntry
        org = make_org()
        entry = AuditEntry.log(
            action="org_created",
            target=org,
            delta={"status": [None, "pending"]},
        )
        self.assertIsNotNone(entry.pk)
        self.assertEqual(entry.action, "org_created")
        self.assertTrue(entry.entry_hash)

    def test_chain_is_valid(self):
        from apps.audit.models import AuditEntry
        org = make_org()
        for i in range(3):
            AuditEntry.log(action="admin_action", target=org, delta={"i": i})
        ok, broken = AuditEntry.verify_chain()
        self.assertTrue(ok)
        self.assertEqual(broken, [])

    def test_first_entry_has_empty_prev_hash(self):
        from apps.audit.models import AuditEntry
        AuditEntry.objects.all().delete()
        entry = AuditEntry.log(action="admin_action")
        self.assertEqual(entry.prev_hash, "")

    def test_second_entry_links_to_first(self):
        from apps.audit.models import AuditEntry
        AuditEntry.objects.all().delete()
        first = AuditEntry.log(action="admin_action")
        second = AuditEntry.log(action="admin_action")
        self.assertEqual(second.prev_hash, first.entry_hash)


# ---------------------------------------------------------------------------
# Public referral form view tests
# ---------------------------------------------------------------------------

class ReferralFormViewTest(TestCase):
    def setUp(self):
        self.org = make_org(referral_delivery_channels=["in_platform"])
        self.url = reverse("referrals:form", kwargs={"org_slug": self.org.slug})

    def test_form_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_submission_without_consent_fails(self):
        response = self.client.post(self.url, {"priority": "normal"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Referral.objects.filter(organization=self.org).exists())

    def test_valid_submission_creates_referral(self):
        response = self.client.post(self.url, {
            "priority": "normal",
            "consent": "1",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Referral.objects.filter(organization=self.org).exists())

    def test_non_accepting_org_returns_404(self):
        self.org.accepts_referrals = False
        self.org.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)


class ReferralSubmittedViewTest(TestCase):
    def setUp(self):
        self.org = make_org(referral_delivery_channels=["in_platform"])

    def test_confirmation_page_loads(self):
        referral = create_referral(org=self.org, form_data={}, pii_dict={"consent": True})
        url = reverse("referrals:submitted", kwargs={"ref": referral.reference_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, referral.reference_number)
