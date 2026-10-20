from math import radians, sin, cos, sqrt, atan2

SCHOOL_LATITUDE = 10.530894609059814
SCHOOL_LONGITUDE = 122.8434738513073
SCHOOL_RADIUS_METERS = 100


def is_inside_school(latitude, longitude):
    earth_radius = 6371000

    lat1 = radians(SCHOOL_LATITUDE)
    lat2 = radians(latitude)
    lat_difference = radians(latitude - SCHOOL_LATITUDE)
    lon_difference = radians(longitude - SCHOOL_LONGITUDE)

    a = (
        sin(lat_difference / 2) ** 2
        + cos(lat1) * cos(lat2)
        * sin(lon_difference / 2) ** 2
    )

    distance = 2 * earth_radius * atan2(
        sqrt(a), sqrt(1 - a)
    )

    return distance <= SCHOOL_RADIUS_METERS
