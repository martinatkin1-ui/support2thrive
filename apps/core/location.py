"""
Geographic search helpers: UK postcodes (postcodes.io), Haversine distance, session/profile location.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from django.conf import settings
from django.http import HttpRequest

# Session keys (anonymous + case worker "search as" override)
SESSION_POSTCODE = "location_postcode"
SESSION_LAT = "location_lat"
SESSION_LNG = "location_lng"
SESSION_LABEL = "location_label"

DEFAULT_RADIUS_MILES = float(getattr(settings, "LOCATION_SEARCH_RADIUS_MILES", 20))
POSTCODES_IO_POSTCODE = "https://api.postcodes.io/postcodes"
REQUEST_TIMEOUT = 8.0


def haversine_miles(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-circle distance in miles (WGS84)."""
    r = 3958.8  # Earth radius in miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_p = p2 - p1
    d_l = math.radians(lon2 - lon1)
    a = math.sin(d_p / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_l / 2) ** 2
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return r * c


def normalize_uk_postcode(raw: str) -> str:
    s = (raw or "").upper().replace(" ", "")
    if len(s) < 5:
        return s
    return s[:-3] + " " + s[-3:]


_uk_postcode_re = re.compile(
    r"^([A-Z]{1,2}\d{1,2}[A-Z]?)\s*(\d[A-Z]{2})$", re.IGNORECASE
)


def is_plausible_uk_postcode(s: str) -> bool:
    t = s.strip()
    if not t:
        return False
    n = normalize_uk_postcode(t)
    return bool(_uk_postcode_re.match(n.replace(" ", "")))


@dataclass
class GeocodeResult:
    ok: bool
    postcode: str = ""
    latitude: float | None = None
    longitude: float | None = None
    admin_district: str = ""
    error: str = ""


def geocode_uk_postcode(raw: str) -> GeocodeResult:
    """
    Resolve a UK postcode to lat/lng via postcodes.io (no API key).
    """
    if not (raw or "").strip():
        return GeocodeResult(ok=False, error="empty")
    compact = re.sub(r"\s+", "", (raw or "").strip().upper())
    if not compact:
        return GeocodeResult(ok=False, error="empty")
    rurl = f"{POSTCODES_IO_POSTCODE}/{quote(compact, safe='')}"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(rurl)
    except httpx.RequestError as e:
        return GeocodeResult(ok=False, error=str(e))

    if resp.status_code == 404:
        return GeocodeResult(ok=False, error="not_found")
    if resp.status_code != 200:
        return GeocodeResult(ok=False, error=f"http_{resp.status_code}")

    data: dict[str, Any] = resp.json()
    if data.get("status") != 200 or not data.get("result"):
        return GeocodeResult(ok=False, error="invalid_response")

    res = data["result"]
    lat = res.get("latitude")
    lon = res.get("longitude")
    if lat is None or lon is None:
        return GeocodeResult(ok=False, error="no_coordinates")

    district = (res.get("admin_district") or res.get("parish") or "") or ""
    pc = (res.get("postcode") or raw).strip()

    return GeocodeResult(
        ok=True,
        postcode=pc,
        latitude=float(lat),
        longitude=float(lon),
        admin_district=district,
    )


def organization_coordinates(org) -> tuple[float, float] | None:
    from apps.organizations.models import Organization

    if not isinstance(org, Organization):
        return None
    if org.latitude is not None and org.longitude is not None:
        return (float(org.latitude), float(org.longitude))
    return None


def get_event_coordinates(event) -> tuple[float, float] | None:
    """Prefer event venue coordinates; else hosting organisation's coordinates."""
    if event.latitude is not None and event.longitude is not None:
        return (float(event.latitude), float(event.longitude))
    if event.organization_id:
        return organization_coordinates(event.organization)
    return None


def get_effective_location(request: HttpRequest) -> dict[str, Any] | None:
    """
    Returns the active search location: session override (case worker / browse-as)
    else authenticated user's home coordinates if set.
    """
    s = request.session
    if s.get(SESSION_LAT) is not None and s.get(SESSION_LNG) is not None:
        return {
            "postcode": (s.get(SESSION_POSTCODE) or "").strip(),
            "lat": float(s[SESSION_LAT]),
            "lng": float(s[SESSION_LNG]),
            "label": (s.get(SESSION_LABEL) or "").strip(),
            "source": "session",
        }

    u = request.user
    if u.is_authenticated:
        if u.home_latitude is not None and u.home_longitude is not None:
            return {
                "postcode": (u.home_postcode or "").strip(),
                "lat": float(u.home_latitude),
                "lng": float(u.home_longitude),
                "label": (u.home_location_label or "").strip(),
                "source": "profile",
            }
    return None


def set_session_location(
    request: HttpRequest,
    *,
    postcode: str,
    lat: float,
    lng: float,
    label: str = "",
) -> None:
    request.session[SESSION_POSTCODE] = postcode
    request.session[SESSION_LAT] = lat
    request.session[SESSION_LNG] = lng
    request.session[SESSION_LABEL] = label
    request.session.modified = True


def clear_session_location(request: HttpRequest) -> None:
    for k in (SESSION_POSTCODE, SESSION_LAT, SESSION_LNG, SESSION_LABEL):
        request.session.pop(k, None)
    request.session.modified = True


def filter_organizations_by_distance(
    organizations,
    lat: float,
    lng: float,
    miles: float | None = None,
) -> list:
    """
    Return list of organizations within radius, sorted by distance.
    Orgs without coordinates are skipped.
    """
    miles = miles if miles is not None else DEFAULT_RADIUS_MILES
    out: list[tuple[Any, float]] = []
    for org in organizations:
        coords = organization_coordinates(org)
        if not coords:
            continue
        d = haversine_miles(lat, lng, coords[0], coords[1])
        if d <= miles:
            out.append((org, d))
    out.sort(key=lambda x: x[1])
    for o, d in out:
        setattr(o, "distance_miles", round(d, 1))
    return [x[0] for x in out]


def filter_occurrences_by_distance(
    occurrences,
    lat: float,
    lng: float,
    miles: float | None = None,
) -> list:
    """EventOccurrence list filtered by distance to venue or org base."""
    miles = miles if miles is not None else DEFAULT_RADIUS_MILES
    out: list[Any] = []
    for occ in occurrences:
        ev = occ.event
        if getattr(ev, "is_online", False) and not (ev.latitude and ev.longitude):
            coords = (
                organization_coordinates(ev.organization) if ev.organization_id else None
            )
        else:
            coords = get_event_coordinates(ev)
        if not coords:
            continue
        d = haversine_miles(lat, lng, coords[0], coords[1])
        if d <= miles:
            setattr(occ, "distance_miles", round(d, 1))
            out.append(occ)
    out.sort(key=lambda o: (o.start, getattr(o, "distance_miles", 0)))
    return out
