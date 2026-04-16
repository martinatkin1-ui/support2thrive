from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views import root_language_redirect

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("", root_language_redirect),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls", namespace="core")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("organizations/", include("apps.organizations.urls", namespace="organizations")),
    path("events/", include("apps.events.urls", namespace="events")),
    path("referrals/", include("apps.referrals.urls", namespace="referrals")),
    path("pathways/", include("apps.pathways.urls", namespace="pathways")),
    path("assistant/", include("apps.assistant.urls", namespace="assistant")),
    path("api/v1/", include("config.api")),
    prefix_default_language=True,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
