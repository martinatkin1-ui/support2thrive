"""Form for OrgDocument — enforces 20MB PDF size limit."""
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import OrgDocument

MAX_PDF_SIZE_BYTES = 20 * 1024 * 1024  # 20MB


class OrgDocumentForm(forms.ModelForm):
    class Meta:
        model = OrgDocument
        fields = ["title", "file"]

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f and f.size > MAX_PDF_SIZE_BYTES:
            raise forms.ValidationError(
                _("PDF must be under 20MB. This file is %(size)s MB.")
                % {"size": round(f.size / 1024 / 1024, 1)}
            )
        return f
