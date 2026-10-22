
import json
import math
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import VisitorForm
from .location_utils import get_school_distance
from .models import Visitor


def get_valid_coordinates(data):
    """Validate latitude and longitude received from the browser."""

    latitude = float(data["latitude"])
    longitude = float(data["longitude"])

    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    ):
        raise ValueError("Invalid coordinates.")

    return latitude, longitude


@require_POST
def check_location(request):
    """Allow visitors within 200 meters of the school."""

    request.session.pop("location_verified", None)
    request.session.pop("verified_latitude", None)
    request.session.pop("verified_longitude", None)

    try:
        data = json.loads(request.body)
        latitude, longitude = get_valid_coordinates(data)

    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):
        return JsonResponse(
            {
                "allowed": False,
                "message": (
                    "Unable to verify your location. "
                    "Please enable location access and try again."
                ),
            },
            status=400,
        )

    distance = get_school_distance(latitude, longitude)
    radius_meters = 200

    print(
        f"Location check: distance={distance:.1f} meters, "
        f"allowed={distance <= radius_meters}",
        flush=True,
    )

    if distance <= radius_meters:
        request.session["location_verified"] = True
        request.session["verified_latitude"] = latitude
        request.session["verified_longitude"] = longitude

        return JsonResponse(
            {
                "allowed": True,
                "message": "Location verified successfully.",
                "distance_meters": round(distance, 1),
                "radius_meters": radius_meters,
            }
        )

    return JsonResponse(
        {
            "allowed": False,
            "message": (
                "You are not within the school premises. "
                "Please proceed to the school location to register."
            ),
        }
    )


def visitor_registration(request):
    """Register visitors only after location verification."""

    if request.method == "POST":
        if request.session.get("location_verified") is not True:
            return JsonResponse(
                {
                    "error": (
                        "Your location verification has expired. "
                        "Please verify your location again."
                    )
                },
                status=403,
            )

        files = request.FILES.copy()
        camera_file = files.get("camera_capture")

        if camera_file:
            files["id_document"] = camera_file

        form = VisitorForm(request.POST, files)

        if form.is_valid():
            visitor = form.save()

            print(
                f"VISITOR SAVED SUCCESSFULLY: ID={visitor.pk}",
                flush=True,
            )

            request.session.pop("location_verified", None)
            request.session.pop("verified_latitude", None)
            request.session.pop("verified_longitude", None)

            return redirect("visitor_success")

        return render(
            request,
            "visitors/registration.html",
            {
                "form": form,
                "show_registration": True,
                "debug": settings.DEBUG,
            },
            status=400,
        )

    form = VisitorForm()

    return render(
        request,
        "visitors/registration.html",
        {
            "form": form,
            "show_registration": False,
            "debug": settings.DEBUG,
        },
    )


def visitor_success(request):
    """Display the successful registration page."""

    return render(request, "visitors/success.html")


@login_required
def staff_dashboard(request):
    """Display visitor records with search and date filtering."""

    today = timezone.localdate()
    visitors = Visitor.objects.all().order_by("-time_in")

    search = request.GET.get("search", "").strip()
    selected_date = request.GET.get("date", "").strip()
    selected_purpose = request.GET.get("purpose", "").strip()

    if search:
        visitors = visitors.filter(
            Q(first_name__icontains=search)
            | Q(middle_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(contact_number__icontains=search)
        )

    if selected_date:
        try:
            chosen_date = date.fromisoformat(selected_date)

            start_datetime = timezone.make_aware(
                datetime.combine(chosen_date, time.min),
                timezone.get_current_timezone(),
            )

            end_datetime = timezone.make_aware(
                datetime.combine(
                    chosen_date + timedelta(days=1),
                    time.min,
                ),
                timezone.get_current_timezone(),
            )

            visitors = visitors.filter(
                time_in__gte=start_datetime,
                time_in__lt=end_datetime,
            )

        except ValueError:
            selected_date = ""

    if selected_purpose:
        visitors = visitors.filter(
            purpose__iexact=selected_purpose
        )

    context = {
        "total_visitors": Visitor.objects.count(),
        "today_visitors": Visitor.objects.filter(
            time_in__date=today
        ).count(),
        "visitors": visitors,
        "search": search,
        "selected_date": selected_date,
        "selected_purpose": selected_purpose,
    }

    return render(
        request,
        "visitors/staff_dashboard.html",
        context,
    )


@login_required
def staff_logout(request):
    """Log out staff and return to the login page."""

    logout(request)
    return redirect("staff_login")
