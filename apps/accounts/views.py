from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from .forms import RegistrationForm


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.role in (user.ROLE_VOLUNTEER, user.ROLE_ORG_MANAGER):
                messages.info(
                    request,
                    _(
                        "Your account has been created and is pending approval. "
                        "You will be notified once an administrator approves your access."
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
