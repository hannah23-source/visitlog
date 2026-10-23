from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.visitor_registration, name="visitor_registration"),
    path("check-location/", views.check_location, name="check_location"),
    path("success/", views.visitor_success, name="visitor_success"),

    # Staff dashboard
    path(
        "staff/dashboard/",
        views.staff_dashboard,
        name="staff_dashboard",
    ),

    # Staff logout
    path(
        "staff/logout/",
        views.staff_logout,
        name="staff_logout",
    ),
]

# Staff login page is available locally only.
if settings.DEBUG:
    urlpatterns += [
        path(
            "staff/login/",
            auth_views.LoginView.as_view(
                template_name="visitors/staff_login.html",
                redirect_authenticated_user=True,
            ),
            name="staff_login",
        ),
    ]
