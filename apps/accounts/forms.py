from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User


class RegistrationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            (User.ROLE_PUBLIC, _("General Public")),
            (User.ROLE_VOLUNTEER, _("Volunteer")),
            (User.ROLE_ORG_MANAGER, _("Organization Manager")),
        ],
        initial=User.ROLE_PUBLIC,
        label=_("Account Type"),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "preferred_language",
            "password1",
            "password2",
        )
