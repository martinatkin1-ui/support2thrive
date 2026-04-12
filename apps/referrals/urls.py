from django.urls import path

from . import views

app_name = "referrals"

urlpatterns = [
    # Public referral form
    path("<slug:org_slug>/refer/", views.referral_form, name="form"),
    path("submitted/<str:ref>/", views.referral_submitted, name="submitted"),

    # Portal — org manager inbox
    path("portal/", views.portal_referral_list, name="portal_list"),
    path("portal/export.csv", views.portal_referral_csv, name="portal_csv"),
    path("portal/<str:ref>/", views.portal_referral_detail, name="portal_detail"),
    path("portal/<str:ref>/acknowledge/", views.portal_acknowledge, name="portal_acknowledge"),
    path("portal/<str:ref>/status/", views.portal_update_status, name="portal_update_status"),
    path("portal/<str:ref>/print/", views.portal_referral_print, name="portal_print"),
]
