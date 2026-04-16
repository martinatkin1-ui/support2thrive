from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import get_language_from_request

from .models import SupportStream


def root_language_redirect(request):
    """
    Map bare `/` to the localized home URL using the same negotiation as
    LocaleMiddleware (session / cookie / Accept-Language), so phones set to
    e.g. Punjabi get `pa` without manually using the language switcher.
    """
    lang = get_language_from_request(request, check_path=False)
    translation.activate(lang)
    return redirect(reverse("core:home"))


def home(request):
    support_streams = SupportStream.objects.all()
    return render(request, "public/home.html", {
        "support_stream_names": [s.name for s in support_streams],
    })
