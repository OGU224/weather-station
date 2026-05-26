"""Device location cache backed by Google Geolocation WiFi scans."""

import logging
import time

import requests

from config import GOOGLE_GEOLOCATION_API_KEY, GOOGLE_GEOLOCATION_ENABLED

logger = logging.getLogger(__name__)

GOOGLE_GEOLOCATION_URL = "https://www.googleapis.com/geolocation/v1/geolocate"
_device_locations = {}
_last_error = None


# Return the latest Google WiFi geolocation error message.
def get_last_device_location_error():
    return _last_error


# Return the last known location for a Core2 device.
def get_device_location(device_id):
    if not device_id:
        return None
    location = _device_locations.get(device_id)
    if not location:
        return None
    return dict(location)


# Normalize visible WiFi access points for Google Geolocation.
def _clean_wifi_access_points(access_points):
    cleaned = []
    seen = set()
    for item in access_points or []:
        mac = str(item.get("macAddress") or item.get("mac") or "").strip().lower()
        if not mac or mac in seen:
            continue
        seen.add(mac)
        entry = {"macAddress": mac}
        try:
            signal = item.get("signalStrength")
            if signal is None:
                signal = item.get("rssi")
            if signal is not None:
                entry["signalStrength"] = int(signal)
        except (TypeError, ValueError):
            pass
        try:
            channel = item.get("channel")
            if channel is not None:
                entry["channel"] = int(channel)
        except (TypeError, ValueError):
            pass
        cleaned.append(entry)
    return cleaned[:20]


# Update a device location using the visible WiFi networks it sent.
def update_device_location_from_wifi(device_id, access_points):
    """Store latest device location from visible WiFi access points."""
    global _last_error

    if not device_id:
        raise ValueError("device_id is required.")
    if not GOOGLE_GEOLOCATION_ENABLED:
        _last_error = "Google Geolocation disabled"
        return None
    if not GOOGLE_GEOLOCATION_API_KEY:
        _last_error = "GOOGLE_GEOLOCATION_API_KEY is missing"
        return None

    wifi_access_points = _clean_wifi_access_points(access_points)
    if len(wifi_access_points) < 2:
        _last_error = "At least two WiFi access points are required"
        return None

    payload = {
        "considerIp": False,
        "wifiAccessPoints": wifi_access_points,
    }
    try:
        response = requests.post(
            GOOGLE_GEOLOCATION_URL,
            params={"key": GOOGLE_GEOLOCATION_API_KEY},
            json=payload,
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
        location = data.get("location") or {}
        lat = location.get("lat")
        lon = location.get("lng")
        if lat is None or lon is None:
            _last_error = "Google Geolocation returned no location"
            return None

        result = {
            "lat": float(lat),
            "lon": float(lon),
            "accuracy_m": data.get("accuracy"),
            "source": "google_wifi",
            "updated_at": time.time(),
            "wifi_count": len(wifi_access_points),
        }
        _device_locations[device_id] = result
        _last_error = None
        return dict(result)
    except Exception as exc:
        _last_error = str(exc)
        logger.warning("Google device geolocation failed: %s", exc)
        return None
