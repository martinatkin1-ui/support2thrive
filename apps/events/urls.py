from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    # Public
    path("", views.event_list, name="list"),
    path("calendar.ics", views.event_ical, name="ical"),
    path("org/<slug:org_slug>/calendar.ics", views.org_event_ical, name="org_ical"),
    path("<slug:slug>/", views.event_detail, name="detail"),

    # Portal — org manager
    path("portal/events/", views.portal_event_list, name="portal_event_list"),
    path("portal/events/new/", views.portal_event_create, name="portal_event_create"),
    path("portal/events/<slug:slug>/edit/", views.portal_event_edit, name="portal_event_edit"),
    path("portal/events/<slug:slug>/delete/", views.portal_event_delete, name="portal_event_delete"),
]
