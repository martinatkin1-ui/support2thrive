from django.test import TestCase
from django.urls import reverse

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
    def test_registration_page_loads(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)

    def test_register_public_user(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": User.ROLE_PUBLIC,
            "phone": "",
            "preferred_language": "en",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newuser")
        self.assertEqual(user.role, User.ROLE_PUBLIC)
        self.assertTrue(user.is_approved)

    def test_register_volunteer_pending(self):
        response = self.client.post(reverse("accounts:register"), {
            "username": "newvol",
            "email": "vol@example.com",
            "first_name": "Vol",
            "last_name": "User",
            "role": User.ROLE_VOLUNTEER,
            "phone": "",
            "preferred_language": "en",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newvol")
        self.assertEqual(user.approval_status, User.APPROVAL_PENDING)


class LoginViewTest(TestCase):
    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
