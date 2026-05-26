"""Approximate weather location from a public IP address.

When the middleware runs locally, no client IP is needed because the server and
Core2 share the same network. When the middleware runs on Cloud Run, callers can
pass the original client IP from X-Forwarded-For so weather follows the device
network instead of the Google server region.
"""

import logging
import time

import requests

from config import (
    IP_GEOLOCATION_CACHE_SECONDS,
    IP_GEOLOCATION_ENABLED,
    IP_GEOLOCATION_URL,
)

logger = logging.getLogger(__name__)

_cached_locations = {}
_last_error = None


def _provider_urls(ip_address=None):
    ip_suffix = "/" + ip_address if ip_address else "/"
    urls = []
    if not ip_address:
        urls.append(IP_GEOLOCATION_URL)
    if ip_address:
        urls.append("https://ipapi.co/" + ip_address + "/json/")
    urls.extend([
        "https://ipwho.is" + ip_suffix,
        "http://ip-api.com/json" + ip_suffix,
    ])
    unique_urls = []
    for url in urls:
        if url and url not in unique_urls:
            unique_urls.append(url)
    return unique_urls


def _parse_location(data):
    if data.get("success") is False or data.get("status") == "fail":
        return None

    lat = data.get("latitude") or data.get("lat")
    lon = data.get("longitude") or data.get("lon")
    if lat is None or lon is None:
        return None

    return {
        "lat": float(lat),
        "lon": float(lon),
        "city": data.get("city") or data.get("regionName") or data.get("region") or "",
    }


def get_last_ip_location_error():
    return _last_error


def get_ip_location(ip_address=None):
    """Return {"lat": float, "lon": float, "city": str} or None."""
    global _last_error

    if not IP_GEOLOCATION_ENABLED:
        _last_error = "IP geolocation disabled"
        return None

    cache_key = ip_address or "server"
    now = time.time()
    cached = _cached_locations.get(cache_key)
    if cached and now - cached["cached_at"] < IP_GEOLOCATION_CACHE_SECONDS:
        return dict(cached["location"])

    errors = []
    for url in _provider_urls(ip_address=ip_address):
        try:
            response = requests.get(url, timeout=4)
            response.raise_for_status()
            location = _parse_location(response.json())
            if location:
                _cached_locations[cache_key] = {
                    "location": location,
                    "cached_at": now,
                }
                _last_error = None
                return dict(location)
            errors.append(url + ": missing location fields")
        except Exception as exc:
            errors.append(url + ": " + str(exc))

    _last_error = "; ".join(errors)
    logger.warning("IP geolocation failed: %s", _last_error)
    return None
