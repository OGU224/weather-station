"""Weather routes under /api/weather."""
from dataclasses import asdict

from flask import Blueprint, jsonify, request

from data.bigquery_client import BigQueryClient
from services.device_location_service import get_device_location, get_last_device_location_error
from services.geolocation_service import get_ip_location, get_last_ip_location_error
from services.weather_service import WeatherService

weather_bp = Blueprint("weather_bp", __name__)
weather_service = WeatherService()
bq_client = BigQueryClient()


# Extract the client IP address from a Flask request.
def _client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    return request.remote_addr


# Decide which city or coordinates should be used for weather.
def _weather_location_args():
    device_id = request.args.get("device_id") or None
    city = request.args.get("city") or None
    country_code = request.args.get("country_code") or request.args.get("country") or None
    lat = request.args.get("lat") or None
    lon = request.args.get("lon") or None
    source = "default"

    if lat is not None and lon is not None:
        try:
            lat = float(lat)
            lon = float(lon)
            source = "query"
        except ValueError:
            lat = None
            lon = None
    else:
        lat = None
        lon = None

    if city:
        source = "query"

    if city is None and lat is None and lon is None and device_id:
        location = get_device_location(device_id)
        if location:
            lat = location.get("lat")
            lon = location.get("lon")
            source = "device_wifi"

    if city is None and lat is None and lon is None:
        location = get_ip_location(ip_address=_client_ip())
        if location:
            lat = location.get("lat")
            lon = location.get("lon")
            source = "ip"

    return (
        {
            "city": city,
            "country_code": country_code,
            "lat": lat,
            "lon": lon,
            "device_id": device_id,
        },
        source,
    )


# Fetch current outdoor weather for the selected location.
@weather_bp.route("/current", methods=["GET"])
def get_current_weather():
    location_args, location_source = _weather_location_args()
    weather_args = dict(location_args)
    weather_args.pop("device_id", None)
    weather = weather_service.get_current_weather(**weather_args)
    if not weather:
        return jsonify({"error": "Meteo indisponible"}), 503

    store = request.args.get("store", "false").lower() == "true"
    if store:
        bq_client.insert_weather_data(weather)

    payload = weather.to_dict()
    payload["location_source"] = location_source
    if location_source == "default":
        payload["location_error"] = get_last_ip_location_error()
    if location_source == "device_wifi":
        payload["location_note"] = "Location estimated from Core2 WiFi scan"
    if location_args.get("lat") is not None and location_args.get("lon") is not None:
        payload["location_lat"] = location_args["lat"]
        payload["location_lon"] = location_args["lon"]
    return jsonify(payload), 200


# Return the forecast for the selected location.
@weather_bp.route("/forecast", methods=["GET"])
def get_weather_forecast():
    """Return 5-day weather forecast from OpenWeatherMap."""
    try:
        days = int(request.args.get("days", 5))
    except ValueError:
        days = 5

    location_args, _ = _weather_location_args()
    weather_args = dict(location_args)
    weather_args.pop("device_id", None)
    forecasts = weather_service.get_forecast(days=days, **weather_args)
    if not forecasts:
        return jsonify({"error": "Forecast indisponible"}), 503

    return jsonify([asdict(f) for f in forecasts]), 200


# Return stored outdoor weather history.
@weather_bp.route("/history", methods=["GET"])
def get_weather_history():
    """Return stored outdoor weather history from BigQuery."""
    try:
        hours = int(request.args.get("hours", 24))
    except ValueError:
        hours = 24

    history = bq_client.get_weather_history(hours=hours)
    results = []
    for row in history:
        ts = row.get("timestamp")
        results.append({
            "timestamp": ts.isoformat() if ts else None,
            "temperature_c": row.get("temperature_c"),
            "feels_like_c": row.get("feels_like_c"),
            "humidity_pct": row.get("humidity_pct"),
            "wind_speed_ms": row.get("wind_speed_ms"),
            "weather_main": row.get("weather_main"),
            "weather_description": row.get("weather_description"),
            "weather_icon": row.get("weather_icon"),
            "city": row.get("city"),
        })
    return jsonify(results), 200
