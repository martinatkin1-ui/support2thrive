from django.urls import path

from . import views

app_name = "pathways"

urlpatterns = [
    path("", views.pathway_list, name="list"),
    path("<slug:slug>/", views.pathway_detail, name="detail"),
]
