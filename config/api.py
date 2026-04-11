from django.urls import include, path

app_name = "api"

urlpatterns = [
    path("auth/", include("apps.accounts.api_urls")),
    path("organizations/", include("apps.organizations.api_urls")),
]
