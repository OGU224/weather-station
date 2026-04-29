"""Flask app principale.
- Factory create_app() qui enregistre les blueprints
- Route /api/health pour verifier que le serveur tourne
- CORS active pour les requetes du M5Stack et Streamlit
- Blueprints : sensor_bp (/api/sensors), weather_bp (/api/weather), voice_bp (/api/voice)
"""
"""Flask app principale."""

import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import FLASK_HOST, FLASK_PORT
from data.bigquery_client import BigQueryClient
from data.models import SensorReading
from services.weather_service import WeatherService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

bq = BigQueryClient()
weather_service = WeatherService()


@app.route("/api/health")
def health():
    return {"status": "ok"}


@app.route("/api/sensors/reading", methods=["POST"])
def post_sensor_reading():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON requis"}), 400

    reading = SensorReading(
        temperature_c=float(data["temperature_c"]),
        humidity_pct=float(data["humidity_pct"]),
        air_quality_index=int(data.get("air_quality_index", 0)),
        motion_detected=bool(data.get("motion_detected", False)),
    )

    ok = bq.insert_sensor_reading(reading)
    logger.info(f"Sensor: {reading.temperature_c}°C {reading.humidity_pct}% → BQ {'OK' if ok else 'ERREUR'}")
    return jsonify({"success": ok, "id": reading.id}), 201 if ok else 500


@app.route("/api/sensors/latest")
def get_latest_sensor():
    result = bq.get_latest_sensor_reading()
    if result:
        return jsonify(result)
    return jsonify({"error": "Aucune donnée"}), 404


@app.route("/api/weather/current")
def get_weather():
    weather = weather_service.get_current_weather()
    if not weather:
        return jsonify({"error": "Météo indisponible"}), 503

    store = request.args.get("store", "false").lower() == "true"
    if store:
        bq.insert_weather_data(weather)

    return jsonify(weather.to_dict())


if __name__ == "__main__":
    logger.info("Flask API démarrée")
    app.run(host=FLASK_HOST, port=int(FLASK_PORT), debug=True)