"""Email notifications triggered by the public registration flow."""

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.translation import gettext as _, override

from .models import User


def _absolute_url(path: str) -> str:
    base = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    return f"{base}{path}" if base else path


def _admin_change_user_url(user_pk) -> str:
    with override("en"):
        path = reverse("admin:accounts_user_change", args=[user_pk])
    return _absolute_url(path)


def notify_org_managers_volunteer_registration(volunteer: User) -> None:
    """Tell organisation managers that a volunteer registered for their org."""
    org = volunteer.organization
    if not org:
        return

    managers = User.objects.filter(
        organization=org,
        role=User.ROLE_ORG_MANAGER,
        is_active=True,
    ).exclude(email="")

    recipient_emails = list({m.email.strip().lower() for m in managers if m.email})
    if not recipient_emails and org.email:
        recipient_emails = [org.email.strip()]
    if not recipient_emails and org.referral_email:
        recipient_emails = [org.referral_email.strip()]
    if not recipient_emails:
        return

    subject = _("New volunteer registration — %(org)s") % {"org": org.name}
    body = _(
        "A new volunteer has registered and is waiting for your approval.\n\n"
        "Name: %(name)s\n"
        "Username: %(username)s\n"
        "Email: %(email)s\n"
        "Organisation: %(org)s\n\n"
        "Review and approve in Django admin:\n"
        "%(url)s\n"
    ) % {
        "name": volunteer.get_full_name() or volunteer.username,
        "username": volunteer.username,
        "email": volunteer.email,
        "org": org.name,
        "url": _admin_change_user_url(volunteer.pk),
    }

    send_mail(
        subject=str(subject),
        message=str(body),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_emails,
        fail_silently=True,
    )


def notify_superusers_org_manager_registration(user: User) -> None:
    """Tell platform superusers that someone registered to manage a new organisation."""
    admins = User.objects.filter(is_superuser=True, is_active=True).exclude(email="")
    recipient_emails = [a.email.strip() for a in admins if a.email]
    if not recipient_emails:
        return

    org = user.organization
    org_name = org.name if org else _("(no organisation record)")
    org_site = org.website if org else ""
    org_contact = org.email if org else ""

    subject = _("New organisation registration — %(name)s") % {"name": org_name}
    body = _(
        "Someone has registered as an organisation representative and needs "
        "platform verification before they can use the portal.\n\n"
        "Representative: %(rep)s\n"
        "Username: %(username)s\n"
        "Login email: %(email)s\n"
        "Organisation: %(org)s\n"
        "Work email (on profile): %(work_email)s\n"
        "Website: %(website)s\n\n"
        "Review in Django admin:\n"
        "%(url)s\n"
    ) % {
        "rep": user.get_full_name() or user.username,
        "username": user.username,
        "email": user.email,
        "org": org_name,
        "work_email": org_contact,
        "website": org_site or _("(not provided)"),
        "url": _admin_change_user_url(user.pk),
    }

    send_mail(
        subject=str(subject),
        message=str(body),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_emails,
        fail_silently=True,
    )
