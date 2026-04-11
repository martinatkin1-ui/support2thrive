from django.urls import path

from . import views

app_name = "organizations"

urlpatterns = [
    path("", views.organization_list, name="list"),
    path("<slug:slug>/", views.organization_detail, name="detail"),
]
