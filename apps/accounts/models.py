import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    ROLE_PUBLIC = "public"
    ROLE_VOLUNTEER = "volunteer"
    ROLE_ORG_MANAGER = "org_manager"
    ROLE_ADMIN = "admin"

    ROLE_CHOICES = [
        (ROLE_PUBLIC, _("General Public")),
        (ROLE_VOLUNTEER, _("Volunteer")),
        (ROLE_ORG_MANAGER, _("Organization Manager")),
        (ROLE_ADMIN, _("Administrator")),
    ]

    APPROVAL_PENDING = "pending"
    APPROVAL_APPROVED = "approved"
    APPROVAL_REJECTED = "rejected"

    APPROVAL_CHOICES = [
        (APPROVAL_PENDING, _("Pending")),
        (APPROVAL_APPROVED, _("Approved")),
        (APPROVAL_REJECTED, _("Rejected")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        _("role"), max_length=20, choices=ROLE_CHOICES, default=ROLE_PUBLIC
    )
    phone = models.CharField(_("phone"), max_length=20, blank=True, default="")
    organization = models.ForeignKey(
        "organizations.Organization",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
        verbose_name=_("organization"),
        help_text=_("Organization this user belongs to"),
    )
    approval_status = models.CharField(
        _("approval status"),
        max_length=20,
        choices=APPROVAL_CHOICES,
        default=APPROVAL_APPROVED,
        help_text=_("Volunteers and managers require approval before accessing the portal"),
    )
    approved_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approvals_given",
        verbose_name=_("approved by"),
    )
    approved_at = models.DateTimeField(_("approved at"), null=True, blank=True)
    preferred_language = models.CharField(
        _("preferred language"),
        max_length=10,
        choices=settings.LANGUAGES,
        default="en",
    )
    last_active = models.DateTimeField(_("last active"), null=True, blank=True)

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_approved(self):
        if self.role == self.ROLE_PUBLIC:
            return True
        return self.approval_status == self.APPROVAL_APPROVED

    def can_manage_org(self, org):
        return self.role == self.ROLE_ADMIN or (
            self.role == self.ROLE_ORG_MANAGER and self.organization == org
        )

    def can_make_referrals(self):
        return self.role in (
            self.ROLE_VOLUNTEER,
            self.ROLE_ORG_MANAGER,
            self.ROLE_ADMIN,
        ) and self.is_approved

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if self.role == self.ROLE_PUBLIC:
            self.approval_status = self.APPROVAL_APPROVED
        elif is_new and self.role in (self.ROLE_VOLUNTEER, self.ROLE_ORG_MANAGER):
            self.approval_status = self.APPROVAL_PENDING
        super().save(*args, **kwargs)
