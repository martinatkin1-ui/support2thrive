from django.shortcuts import redirect
from django.urls import reverse


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
        # Only intercept portal pages; let public browsing, admin, and accounts pass
        if (
            request.user.is_authenticated
            and getattr(request.user, "role", None) == "org_manager"
            and "/portal/" in path
            and "/portal/onboarding/" not in path
        ):
            org = getattr(request.user, "organization", None)
            if org and not org.onboarding_complete:
                return redirect(reverse("organizations:onboarding"))

        return self.get_response(request)
