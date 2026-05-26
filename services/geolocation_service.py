"""Approximate middleware geolocation from public IP.

This is used only when the caller does not provide a weather location. It works
well for the local demo because the Core2 and laptop share the same network.
When deployed to the cloud, this gives the server location, not the device.
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

_cached_location = None
_cached_at = 0
_last_error = None


def _provider_urls():
    urls = [
        IP_GEOLOCATION_URL,
        "https://ipwho.is/",
        "http://ip-api.com/json/",
    ]
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


def get_ip_location():
    """Return {"lat": float, "lon": float, "city": str} or None."""
    global _cached_location, _cached_at, _last_error

    if not IP_GEOLOCATION_ENABLED:
        _last_error = "IP geolocation disabled"
        return None

    now = time.time()
    if _cached_location and now - _cached_at < IP_GEOLOCATION_CACHE_SECONDS:
        return dict(_cached_location)

    errors = []
    for url in _provider_urls():
        try:
            response = requests.get(url, timeout=4)
            response.raise_for_status()
            location = _parse_location(response.json())
            if location:
                _cached_location = location
                _cached_at = now
                _last_error = None
                return dict(_cached_location)
            errors.append(url + ": missing location fields")
        except Exception as exc:
            errors.append(url + ": " + str(exc))

    _last_error = "; ".join(errors)
    logger.warning("IP geolocation failed: %s", _last_error)
    return None
