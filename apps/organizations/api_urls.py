from django.urls import path

from . import api_views

urlpatterns = [
    path("", api_views.OrganizationListView.as_view(), name="organization-list"),
    path("<slug:slug>/", api_views.OrganizationDetailView.as_view(), name="organization-detail"),
]
