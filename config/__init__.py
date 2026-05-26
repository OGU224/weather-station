"""Central configuration allows easy change of parameters (python bridge), instead of having evry file going through .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=False)


def _get(key, default=""):
    return os.getenv(key, default)


def _get_int(key, default=0):
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


# OpenWeatherMap
OWM_API_KEY = _get("OWM_API_KEY")
OWM_CITY = _get("OWM_CITY", "Lausanne")
OWM_COUNTRY_CODE = _get("OWM_COUNTRY_CODE", "CH")
#metric that OWM accepts
OWM_UNITS = _get("OWM_UNITS", "metric")
OWM_LANG = _get("OWM_LANG", "fr")
OWM_BASE_URL = "https://api.openweathermap.org/data/2.5"
IP_GEOLOCATION_ENABLED = _get("IP_GEOLOCATION_ENABLED", "true").lower() == "true"
IP_GEOLOCATION_URL = _get("IP_GEOLOCATION_URL", "https://ipapi.co/json/")
IP_GEOLOCATION_CACHE_SECONDS = _get_int("IP_GEOLOCATION_CACHE_SECONDS", 1800)
GOOGLE_GEOLOCATION_ENABLED = _get("GOOGLE_GEOLOCATION_ENABLED", "false").lower() == "true"
GOOGLE_GEOLOCATION_API_KEY = _get("GOOGLE_GEOLOCATION_API_KEY")

#Google Cloud
GCP_PROJECT = _get("GOOGLE_CLOUD_PROJECT")
BQ_DATASET = _get("BQ_DATASET", "weather_station")
BQ_TABLE_SENSORS = "sensor_readings"
BQ_TABLE_WEATHER = "weather_history"

#Flask
FLASK_HOST = _get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = _get_int("FLASK_PORT", 5000)

def get_bq_table_id(table_name):
    return f"{GCP_PROJECT}.{BQ_DATASET}.{table_name}"
