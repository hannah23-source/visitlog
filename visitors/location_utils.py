from math import radians, sin, cos, sqrt, atan2

# School coordinates
SCHOOL_LATITUDE = 10.530894609059814
SCHOOL_LONGITUDE = 122.8434738513073

# Allowed distance from the school
SCHOOL_RADIUS_METERS = 200


def get_school_distance(latitude, longitude):
    """Calculate distance from the school in meters."""

    earth_radius = 6_371_000

    lat1 = radians(SCHOOL_LATITUDE)
    lat2 = radians(latitude)

    lat_difference = radians(latitude - SCHOOL_LATITUDE)
    lon_difference = radians(longitude - SCHOOL_LONGITUDE)

    a = (
        sin(lat_difference / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(lon_difference / 2) ** 2
    )

    # Protect against floating-point rounding errors
    a = max(0.0, min(1.0, a))

    distance = 2 * earth_radius * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return distance


def is_inside_school(latitude, longitude):
    """Check whether coordinates are within the school radius."""

    distance = get_school_distance(latitude, longitude)

    return distance <= SCHOOL_RADIUS_METERS
