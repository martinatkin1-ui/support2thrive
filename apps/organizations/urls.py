from django.urls import path

from . import onboarding_views, views

app_name = "organizations"

urlpatterns = [
    # Public
    path("", views.organization_list, name="list"),
    path("<slug:slug>/", views.organization_detail, name="detail"),

    # Onboarding wizard
    path("portal/onboarding/", onboarding_views.onboarding_wizard, name="onboarding"),
    path("portal/onboarding/<str:step>/", onboarding_views.onboarding_wizard, name="onboarding_step"),

    # Portal dashboard (post-onboarding)
    path("portal/dashboard/", onboarding_views.portal_dashboard, name="portal_dashboard"),
]
