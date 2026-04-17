"""Shared organisation helpers (registration, imports, etc.)."""

from django.utils.text import slugify
from django.utils.translation import gettext as _

from .models import Organization


def create_pending_organization_for_registration(*, name, work_email, website):
    """
    Create a shell organisation for a new organisation-manager signup.
    Stays status=pending until onboarding is completed (then becomes active).
    """
    name = (name or "").strip()
    base = slugify(name)[:80] or "organisation"
    slug = base
    suffix = 0
    while Organization.objects.filter(slug=slug).exists():
        suffix += 1
        slug = f"{base}-{suffix}"

    return Organization.objects.create(
        name=name,
        slug=slug,
        description=_(
            "This organisation profile is awaiting platform verification. "
            "The representative will add full details during onboarding."
        ),
        short_description=_("Pending verification")[:300],
        status="pending",
        email=(work_email or "").strip(),
        website=(website or "").strip(),
    )
