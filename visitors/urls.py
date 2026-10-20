from django.urls import path
from . import views

urlpatterns = [
    path("", views.visitor_registration, name="visitor_registration"),
    path("check-location/", views.check_location, name="check_location"),
    path("success/", views.visitor_success, name="visitor_success"),
    path("staff/dashboard/", views.staff_dashboard, name="staff_dashboard"),
]
