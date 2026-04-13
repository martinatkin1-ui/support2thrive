from django.urls import path

from . import onboarding_views, views

app_name = "organizations"

urlpatterns = [
    # Public list
    path("", views.organization_list, name="list"),

    # Portal routes must come before the slug catch-all — "portal" is a valid slug
    path("portal/onboarding/", onboarding_views.onboarding_wizard, name="onboarding"),
    path("portal/onboarding/<str:step>/", onboarding_views.onboarding_wizard, name="onboarding_step"),
    path("portal/dashboard/", onboarding_views.portal_dashboard, name="portal_dashboard"),

    # Public org detail — must be last so portal routes are matched first
    path("<slug:slug>/", views.organization_detail, name="detail"),
]
