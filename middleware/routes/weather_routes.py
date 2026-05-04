"""Routes meteo — /api/weather/"""
from flask import Blueprint, jsonify, request
from services.weather_service import WeatherService
from data.bigquery_client import BigQueryClient
from dataclasses import asdict

weather_bp = Blueprint('weather_bp', __name__)
weather_service = WeatherService()
bq_client = BigQueryClient()


@weather_bp.route('/current', methods=['GET'])
def get_current_weather():
    weather = weather_service.get_current_weather()
    if not weather:
        return jsonify({"error": "Météo indisponible"}), 503

    store = request.args.get("store", "false").lower() == "true"
    if store:
        bq_client.insert_weather_data(weather)

    return jsonify(weather.to_dict()), 200


@weather_bp.route('/forecast', methods=['GET'])
def get_weather_forecast():
    """Return 5-day weather forecast from OpenWeatherMap."""
    try:
        days = int(request.args.get("days", 5))
    except ValueError:
        days = 5

    forecasts = weather_service.get_forecast(days=days)
    if not forecasts:
        return jsonify({"error": "Forecast indisponible"}), 503

    return jsonify([asdict(f) for f in forecasts]), 200


@weather_bp.route('/history', methods=['GET'])
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
