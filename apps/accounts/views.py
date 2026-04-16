from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_protect

from .forms import RegistrationForm
from .models import User
from .registration_notifications import (
    notify_org_managers_volunteer_registration,
    notify_superusers_org_manager_registration,
)


class OrgAwareLoginView(LoginView):
    """
    After login, approved organisation managers go straight to the portal onboarding
    wizard (or the portal dashboard if onboarding is already complete). Everyone
    else defaults to their profile. A safe ?next= URL always wins.
    """

    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        user = self.request.user
        if (
            user.is_authenticated
            and getattr(user, "role", None) == User.ROLE_ORG_MANAGER
            and user.is_approved
        ):
            org = getattr(user, "organization", None)
            if org is not None:
                if org.onboarding_complete:
                    return reverse("organizations:portal_dashboard")
                return reverse("organizations:onboarding")
        return reverse("accounts:profile")


@method_decorator(csrf_protect, name="dispatch")
class AccountLogoutView(View):
    """
    GET: confirmation page (Django’s built-in LogoutView is POST-only; plain /logout/
    links must not use GET to clear the session).
    POST: end the session and redirect home, or a safe ?next= / form next URL.
    """

    http_method_names = ["get", "post", "head", "options"]

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("core:home")
        next_url = request.GET.get("next", "")
        return render(
            request,
            "accounts/logout_confirm.html",
            {"next_url": next_url},
        )

    def post(self, request):
        next_url = (request.POST.get("next") or "").strip()
        if request.user.is_authenticated:
            logout(request)
            messages.success(request, _("You have been signed out."))
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect("core:home")


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.role == user.ROLE_VOLUNTEER:
                notify_org_managers_volunteer_registration(user)
                messages.info(
                    request,
                    _(
                        "Your account has been created. Your organisation’s managers "
                        "have been notified and will verify your access. "
                        "You can log in once they approve your account."
                    ),
                )
            elif user.role == user.ROLE_ORG_MANAGER:
                notify_superusers_org_manager_registration(user)
                messages.info(
                    request,
                    _(
                        "Your account and organisation profile have been created and are "
                        "pending verification by the platform team. "
                        "After approval, your first login will open the organisation setup "
                        "wizard so you can publish your profile."
                    ),
                )
            else:
                messages.success(request, _("Your account has been created successfully."))
            return redirect("accounts:login")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def profile(request):
    return render(request, "accounts/profile.html")
