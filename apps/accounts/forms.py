from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from apps.organizations.models import Organization
from apps.organizations.services import create_pending_organization_for_registration

from .models import User


class RegistrationForm(UserCreationForm):
    role = forms.ChoiceField(
        label=_("How will you use this platform?"),
        choices=[
            (
                User.ROLE_PUBLIC,
                _("Personal account — browse services and events"),
            ),
            (
                User.ROLE_VOLUNTEER,
                _("Volunteer — I help at an existing organisation"),
            ),
            (
                User.ROLE_ORG_MANAGER,
                _("Organisation — I manage our organisation on the platform"),
            ),
        ],
        initial=User.ROLE_PUBLIC,
        widget=forms.Select(attrs={"class": "registration-role-select"}),
    )

    volunteer_organization = forms.ModelChoiceField(
        label=_("Which organisation do you volunteer with?"),
        queryset=Organization.objects.filter(status="active").order_by("name"),
        required=False,
        empty_label=_("Select an organisation…"),
        widget=forms.Select(attrs={"class": "w-full rounded-md border-gray-300"}),
    )

    organization_name = forms.CharField(
        label=_("Organisation name"),
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "organization",
                "class": "w-full rounded-md border-gray-300 shadow-sm px-3 py-2 border",
            }
        ),
    )

    organization_work_email = forms.EmailField(
        label=_("Organisation work email"),
        required=False,
        help_text=_(
            "We use this to verify your organisation. It may be shown to platform administrators only."
        ),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "class": "w-full rounded-md border-gray-300 shadow-sm px-3 py-2 border",
            }
        ),
    )

    organization_website = forms.URLField(
        label=_("Organisation website"),
        required=False,
        widget=forms.URLInput(
            attrs={
                "placeholder": "https://",
                "class": "w-full rounded-md border-gray-300 shadow-sm px-3 py-2 border",
            }
        ),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "preferred_language",
            "password1",
            "password2",
            "role",
            "volunteer_organization",
            "organization_name",
            "organization_work_email",
            "organization_website",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("username", "email", "first_name", "last_name", "phone"):
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault(
                    "class",
                    "w-full rounded-md border-gray-300 shadow-sm px-3 py-2 border",
                )
        for name in ("password1", "password2"):
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault(
                    "class",
                    "w-full rounded-md border-gray-300 shadow-sm px-3 py-2 border",
                )
        if "preferred_language" in self.fields:
            self.fields["preferred_language"].widget.attrs.setdefault(
                "class",
                "w-full rounded-md border-gray-300 shadow-sm px-3 py-2 border",
            )
        if "role" in self.fields:
            self.fields["role"].widget.attrs.setdefault(
                "class",
                "w-full rounded-md border-gray-300 shadow-sm px-3 py-2 border registration-role-select",
            )

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")

        if role == User.ROLE_VOLUNTEER:
            org = cleaned.get("volunteer_organization")
            if not org:
                self.add_error(
                    "volunteer_organization",
                    _("Please select the organisation you volunteer with."),
                )
            cleaned["organization_name"] = ""
            cleaned["organization_work_email"] = ""
            cleaned["organization_website"] = ""

        elif role == User.ROLE_ORG_MANAGER:
            name = (cleaned.get("organization_name") or "").strip()
            work_email = (cleaned.get("organization_work_email") or "").strip()
            website = (cleaned.get("organization_website") or "").strip()
            if not name:
                self.add_error(
                    "organization_name",
                    _("Enter your organisation’s name."),
                )
            if not work_email:
                self.add_error(
                    "organization_work_email",
                    _("Enter a work email we can use to verify your organisation."),
                )
            if not website:
                self.add_error(
                    "organization_website",
                    _("Enter your organisation’s website."),
                )
            cleaned["volunteer_organization"] = None

        else:
            cleaned["volunteer_organization"] = None
            cleaned["organization_name"] = ""
            cleaned["organization_work_email"] = ""
            cleaned["organization_website"] = ""

        return cleaned

    def save(self, commit=True):
        user: User = super().save(commit=False)
        role = self.cleaned_data["role"]

        if role == User.ROLE_VOLUNTEER:
            user.organization = self.cleaned_data["volunteer_organization"]

        elif role == User.ROLE_ORG_MANAGER:
            org = create_pending_organization_for_registration(
                name=self.cleaned_data["organization_name"],
                work_email=self.cleaned_data["organization_work_email"],
                website=self.cleaned_data["organization_website"],
            )
            user.organization = org

        else:
            user.organization = None

        if commit:
            user.save()
        return user
