from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("location/", views.set_location, name="set_location"),
    path("location/clear/", views.clear_browse_location, name="clear_location"),
]
