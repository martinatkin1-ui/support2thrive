from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _

from apps.accounts.models import User


class OnboardingRedirectMiddleware:
    """
    Redirect org_managers with incomplete onboarding to the wizard on every
    portal request. Uses substring matching to handle i18n language prefixes
    (e.g. /en/organizations/portal/onboarding/).

    Only intercepts /portal/ paths — public browsing is unaffected.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not request.user.is_authenticated:
            return self.get_response(request)

        role = getattr(request.user, "role", None)
        # Block portal for volunteers and org managers until an administrator approves them
        if (
            role in (User.ROLE_VOLUNTEER, User.ROLE_ORG_MANAGER)
            and "/organizations/portal/" in path
            and not request.user.is_approved
        ):
            messages.info(
                request,
                _("Your account is waiting for verification. We will email you when you can use the portal."),
            )
            return redirect("accounts:profile")

        # Only intercept portal pages; let public browsing, admin, and accounts pass
        if (
            role == User.ROLE_ORG_MANAGER
            and "/portal/" in path
            and "/portal/onboarding/" not in path
        ):
            org = getattr(request.user, "organization", None)
            if org and not org.onboarding_complete:
                return redirect(reverse("organizations:onboarding"))

        return self.get_response(request)
