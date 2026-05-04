"""
Configuration centrale.
Charge les variables depuis .env et expose des constantes.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)


def _get(key, default=""):
    return os.getenv(key, default)


def _get_int(key, default=0):
    return int(os.getenv(key, str(default)))


# --- OpenWeatherMap ---
OWM_API_KEY = _get("OWM_API_KEY")
OWM_CITY = _get("OWM_CITY", "Lausanne")
OWM_COUNTRY_CODE = _get("OWM_COUNTRY_CODE", "CH")
OWM_UNITS = "metric"
OWM_LANG = "fr"
OWM_BASE_URL = "https://api.openweathermap.org/data/2.5"

# --- Google Cloud ---
GCP_PROJECT = _get("GOOGLE_CLOUD_PROJECT")
GCP_CREDENTIALS = _get("GOOGLE_APPLICATION_CREDENTIALS")
BQ_DATASET = _get("BQ_DATASET", "weather_station")
BQ_TABLE_SENSORS = "sensor_readings"
BQ_TABLE_WEATHER = "weather_history"

# --- Device ---
DEVICE_ID = _get("DEVICE_ID", "m5stack-01")
HUMIDITY_ALERT_THRESHOLD = _get_int("HUMIDITY_ALERT_THRESHOLD", 40)

# --- Flask ---
FLASK_HOST = _get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = _get_int("FLASK_PORT", 5000)

def get_bq_table_id(table_name):
    return f"{GCP_PROJECT}.{BQ_DATASET}.{table_name}"
