"""Distances, outlines and Plus Codes.

Every constant and formula here matches the N-Ways issuer, so a deployment of
this server takes the same decisions at the same distances:

* ``plane_m``: the local plane used for a new home's nearest area
  (110,574 m per degree of latitude, 111,320 x cos(lat) per degree of longitude);
* ``door_m``: the rule for "another door of this compound" and for moving an
  entrance (111,320 m per degree on both axes, cosine of the mean latitude);
* ``ground_m``: the distance on the WGS 84 ellipsoid, for "the code at this
  point" and the radius searches (the issuer measures on the ellipsoid too).
"""
import math

M_LAT = 110574.0
M_LON_EQ = 111320.0

# WGS 84
_A = 6378137.0
_F = 1 / 298.257223563
_E2 = _F * (2 - _F)


def plane_m(lat1, lon1, lat2, lon2):
    """Distance on the local plane, cosine of the second point's latitude."""
    return math.hypot((lat1 - lat2) * M_LAT, (lon1 - lon2) * M_LON_EQ * math.cos(math.radians(lat2)))


def door_m(lat1, lng1, lat2, lng2):
    """Distance for the 80 m door and entrance rules."""
    dy = (lat2 - lat1) * 111320
    dx = (lng2 - lng1) * 111320 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def ground_m(lat1, lng1, lat2, lng2):
    """Distance on the WGS 84 ellipsoid, from its radii of curvature at the mean
    latitude. Within a few kilometres it agrees with a geodesic to the millimetre."""
    phi = math.radians((lat1 + lat2) / 2)
    s = math.sin(phi)
    w = math.sqrt(1 - _E2 * s * s)
    m = _A * (1 - _E2) / (w ** 3)   # meridian radius
    n = _A / w                      # prime-vertical radius
    dy = math.radians(lat2 - lat1) * m
    dx = math.radians(lng2 - lng1) * n * math.cos(phi)
    return math.hypot(dx, dy)


def box_around(lat, lng, metres):
    """(min_lat, max_lat, min_lng, max_lng) holding every point within ``metres``."""
    dlat = metres / 110000.0
    dlng = metres / (110000.0 * max(0.05, math.cos(math.radians(lat))))
    return lat - dlat, lat + dlat, lng - dlng, lng + dlng


def open_ring(ring):
    """The ring without a repeated closing point."""
    ring = [(float(p[0]), float(p[1])) for p in ring]
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring = ring[:-1]
    return ring


def ring_area_m2(ring):
    """Area of an outline ([lng, lat] points), on the plane of its first point."""
    if len(ring) < 3:
        return 0.0
    k = math.cos(math.radians(ring[0][1]))
    a = 0.0
    for i in range(len(ring)):
        j = (i + 1) % len(ring)
        xi, yi = ring[i][0] * M_LON_EQ * k, ring[i][1] * M_LAT
        xj, yj = ring[j][0] * M_LON_EQ * k, ring[j][1] * M_LAT
        a += xi * yj - xj * yi
    return abs(a) / 2


def in_ring(lng, lat, ring):
    """Even-odd rule, [lng, lat] points."""
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def ring_centroid(ring):
    """Area-weighted centre of an outline (the vertex mean for a degenerate one)."""
    a = cx = cy = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    if abs(a) < 1e-18:
        return sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    return cx / (3 * a), cy / (3 * a)


_OLC = '23456789CFGHJMPQRVWX'


def plus_code(lat, lng):
    """Open Location Code of a point, 11 characters ("6FGFCC5J+CH2")."""
    def r6(x):
        return round(x * 1e6) / 1e6
    lat = min(90.0, max(-90.0, lat))
    lng = ((lng + 180) % 360 + 360) % 360 - 180
    lat_v = int(math.floor(r6((lat + 90) * 25000000)))
    lng_v = int(math.floor(r6((lng + 180) * 8192000)))
    tail = ''
    for _ in range(5):
        tail = _OLC[(lat_v % 5) * 4 + lng_v % 4] + tail
        lat_v //= 5
        lng_v //= 4
    pairs = ''
    for _ in range(5):
        pairs = _OLC[lat_v % 20] + _OLC[lng_v % 20] + pairs
        lat_v //= 20
        lng_v //= 20
    full = pairs + tail
    return full[:8] + '+' + full[8:11]
