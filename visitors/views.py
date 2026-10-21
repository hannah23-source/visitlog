
import json
import math

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
    """Validate latitude and longitude from the browser."""

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
    """Check whether the visitor is inside the school geofence."""

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
        print(
            "Location check failed: invalid location data.",
            flush=True,
        )

        return JsonResponse(
            {
                "allowed": False,
                "message": "Invalid location data. Please try again.",
            },
            status=400,
        )

    distance = get_school_distance(latitude, longitude)
    radius_meters = 200
    allowed = distance <= radius_meters

    print(
        f"Location check: latitude={latitude}, "
        f"longitude={longitude}, "
        f"distance={distance:.1f} meters, "
        f"allowed={allowed}",
        flush=True,
    )

    if allowed:
        request.session["location_verified"] = True
        request.session["verified_latitude"] = latitude
        request.session["verified_longitude"] = longitude

        return JsonResponse(
            {
                "allowed": True,
                "message": (
                    "Location verified. "
                    f"Distance from school: {distance:.1f} meters."
                ),
                "distance_meters": round(distance, 1),
                "radius_meters": radius_meters,
            }
        )

    return JsonResponse(
        {
            "allowed": False,
            "message": (
                "You are outside the school location. "
                f"Detected distance: {distance:.1f} meters; "
                f"allowed radius: {radius_meters} meters."
            ),
            "distance_meters": round(distance, 1),
            "radius_meters": radius_meters,
        }
    )


def visitor_registration(request):
    """Register a visitor after successful location verification."""

    if request.method == "POST":

        if request.session.get("location_verified") is not True:
            return JsonResponse(
                {
                    "error": (
                        "Please verify your location before registering."
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
            form.save()

            request.session.pop("location_verified", None)
            request.session.pop("verified_latitude", None)
            request.session.pop("verified_longitude", None)

            return redirect("visitor_success")

    else:
        form = VisitorForm()

    return render(
        request,
        "visitors/registration.html",
        {"form": form},
    )


def visitor_success(request):
    """Display the successful registration page."""

    return render(
        request,
        "visitors/success.html",
    )


@login_required
def staff_dashboard(request):
    """Display visitor records and dashboard statistics."""

    today = timezone.localdate()
    visitors = Visitor.objects.all().order_by("-time_in")

    search = request.GET.get("search", "").strip()
    month = request.GET.get("month", "")
    year = request.GET.get("year", "")

    if search:
        visitors = visitors.filter(
            Q(first_name__icontains=search)
            | Q(middle_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(contact_number__icontains=search)
        )

    if month.isdigit() and 1 <= int(month) <= 12:
        visitors = visitors.filter(
            time_in__month=int(month)
        )

    if year.isdigit() and 2000 <= int(year) <= 2100:
        visitors = visitors.filter(
            time_in__year=int(year)
        )

    context = {
        "total_visitors": Visitor.objects.count(),
        "today_visitors": Visitor.objects.filter(
            time_in__date=today
        ).count(),
        "visitors": visitors,
        "search": search,
        "selected_month": month,
        "selected_year": year,
    }

    return render(
        request,
        "visitors/staff_dashboard.html",
        context,
    )

