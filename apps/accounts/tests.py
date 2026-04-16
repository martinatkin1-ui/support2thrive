from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.organizations.models import Organization, OrgOnboardingState

from .models import User


class UserModelTest(TestCase):
    def test_public_user_auto_approved(self):
        user = User.objects.create_user(
            username="publicuser", password="testpass123", role=User.ROLE_PUBLIC
        )
        self.assertTrue(user.is_approved)
        self.assertEqual(user.approval_status, User.APPROVAL_APPROVED)

    def test_volunteer_pending_on_create(self):
        user = User.objects.create_user(
            username="volunteer1", password="testpass123", role=User.ROLE_VOLUNTEER
        )
        self.assertFalse(user.is_approved)
        self.assertEqual(user.approval_status, User.APPROVAL_PENDING)

    def test_org_manager_pending_on_create(self):
        user = User.objects.create_user(
            username="manager1", password="testpass123", role=User.ROLE_ORG_MANAGER
        )
        self.assertFalse(user.is_approved)
        self.assertEqual(user.approval_status, User.APPROVAL_PENDING)

    def test_can_make_referrals_requires_approval(self):
        user = User.objects.create_user(
            username="vol", password="testpass123", role=User.ROLE_VOLUNTEER
        )
        self.assertFalse(user.can_make_referrals())

        user.approval_status = User.APPROVAL_APPROVED
        user.save()
        self.assertTrue(user.can_make_referrals())

    def test_public_cannot_make_referrals(self):
        user = User.objects.create_user(
            username="pub", password="testpass123", role=User.ROLE_PUBLIC
        )
        self.assertFalse(user.can_make_referrals())


class RegistrationViewTest(TestCase):
    def setUp(self):
        self.partner_org = Organization.objects.create(
            name="Partner Org",
            slug="partner-org",
            description="Description",
            short_description="Short",
            status="active",
        )

    def test_registration_page_loads(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)

    def _post_base(self, **extra):
        data = {
            "username": extra.pop("username", "newuser"),
            "email": extra.pop("email", "new@example.com"),
            "first_name": "Test",
            "last_name": "User",
            "phone": "",
            "preferred_language": "en",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        data.update(extra)
        return self.client.post(reverse("accounts:register"), data)

    def test_register_public_user(self):
        response = self._post_base(
            username="newuser",
            email="new@example.com",
            role=User.ROLE_PUBLIC,
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newuser")
        self.assertEqual(user.role, User.ROLE_PUBLIC)
        self.assertTrue(user.is_approved)
        self.assertIsNone(user.organization)

    def test_register_volunteer_pending(self):
        response = self._post_base(
            username="newvol",
            email="vol@example.com",
            role=User.ROLE_VOLUNTEER,
            volunteer_organization=self.partner_org.pk,
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newvol")
        self.assertEqual(user.approval_status, User.APPROVAL_PENDING)
        self.assertEqual(user.organization_id, self.partner_org.pk)

    def test_register_volunteer_requires_organisation(self):
        response = self._post_base(
            username="novolorg",
            role=User.ROLE_VOLUNTEER,
            volunteer_organization="",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="novolorg").exists())

    def test_register_org_manager_creates_pending_organisation(self):
        before = Organization.objects.count()
        response = self._post_base(
            username="newmgr",
            email="mgr.person@example.com",
            role=User.ROLE_ORG_MANAGER,
            organization_name="Fresh Charity",
            organization_work_email="office@freshcharity.example",
            organization_website="https://freshcharity.example",
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Organization.objects.count(), before + 1)
        user = User.objects.get(username="newmgr")
        self.assertEqual(user.approval_status, User.APPROVAL_PENDING)
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.name, "Fresh Charity")
        self.assertEqual(user.organization.status, "pending")
        self.assertEqual(user.organization.email, "office@freshcharity.example")

    def test_register_volunteer_notifies_org_managers(self):
        User.objects.create_user(
            username="om",
            password="x",
            email="manager@partner.example",
            role=User.ROLE_ORG_MANAGER,
            organization=self.partner_org,
            approval_status=User.APPROVAL_APPROVED,
        )
        mail.outbox.clear()
        self._post_base(
            username="newvol2",
            email="vol2@example.com",
            role=User.ROLE_VOLUNTEER,
            volunteer_organization=self.partner_org.pk,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("manager@partner.example", mail.outbox[0].to)

    def test_register_org_manager_notifies_superusers(self):
        User.objects.create_superuser("su", "super@example.com", "su-pass-12345")
        mail.outbox.clear()
        self._post_base(
            username="newmgr2",
            email="rep@example.com",
            role=User.ROLE_ORG_MANAGER,
            organization_name="Another Org",
            organization_work_email="hello@another.example",
            organization_website="https://another.example",
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("super@example.com", mail.outbox[0].to)

    def test_pending_org_manager_cannot_access_portal(self):
        org = Organization.objects.create(
            name="Shell Org",
            slug="shell-org",
            description="D",
            short_description="S",
            status="pending",
        )
        manager = User.objects.create_user(
            username="pendmgr",
            password="x",
            role=User.ROLE_ORG_MANAGER,
            organization=org,
        )
        self.assertEqual(manager.approval_status, User.APPROVAL_PENDING)
        self.client.force_login(manager)
        response = self.client.get(reverse("organizations:onboarding"))
        self.assertRedirects(response, reverse("accounts:profile"))


class LoginViewTest(TestCase):
    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)


class AccountLogoutViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="logoutuser",
            password="SecretPass123!",
            role=User.ROLE_PUBLIC,
        )

    def test_get_logout_redirects_anonymous_to_home(self):
        response = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("core:home"))

    def test_get_logout_shows_confirm_when_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/logout_confirm.html")

    def test_post_logout_clears_session_and_redirects_home(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("core:home"))
        follow = self.client.get(reverse("accounts:logout"))
        self.assertRedirects(follow, reverse("core:home"))

    def test_post_logout_accepts_safe_relative_next(self):
        self.client.force_login(self.user)
        next_path = reverse("accounts:login")
        response = self.client.post(reverse("accounts:logout"), {"next": next_path})
        self.assertRedirects(response, next_path, fetch_redirect_response=False)

    def test_post_logout_ignores_unsafe_next(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("accounts:logout"),
            {"next": "https://evil.example.net/phish"},
        )
        self.assertRedirects(response, reverse("core:home"))


class OrgAwareLoginRedirectTest(TestCase):
    """Approved organisation managers land on onboarding (or dashboard) after login."""

    def setUp(self):
        self.org = Organization.objects.create(
            name="Portal Org",
            slug="portal-org",
            description="D",
            short_description="S",
            status="pending",
        )

    def test_approved_org_manager_redirects_to_onboarding(self):
        u = User.objects.create_user(
            username="om",
            password="SecretPass123!",
            role=User.ROLE_ORG_MANAGER,
            organization=self.org,
        )
        u.approval_status = User.APPROVAL_APPROVED
        u.save(update_fields=["approval_status"])
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "om", "password": "SecretPass123!"},
        )
        self.assertRedirects(response, reverse("organizations:onboarding"))

    def test_approved_org_manager_completed_onboarding_goes_to_dashboard(self):
        OrgOnboardingState.objects.create(
            organization=self.org,
            is_complete=True,
            completed_steps=["about", "services", "referral_config", "scraping", "review"],
        )
        u = User.objects.create_user(
            username="om2",
            password="SecretPass123!",
            role=User.ROLE_ORG_MANAGER,
            organization=self.org,
        )
        u.approval_status = User.APPROVAL_APPROVED
        u.save(update_fields=["approval_status"])
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "om2", "password": "SecretPass123!"},
        )
        self.assertRedirects(response, reverse("organizations:portal_dashboard"))

    def test_public_user_redirects_to_profile(self):
        User.objects.create_user(
            username="pub",
            password="SecretPass123!",
            role=User.ROLE_PUBLIC,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "pub", "password": "SecretPass123!"},
        )
        self.assertRedirects(response, reverse("accounts:profile"))
