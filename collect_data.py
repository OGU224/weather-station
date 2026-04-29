"""
Collecte automatique de la météo outdoor toutes les 10 min.
Usage: python collect_data.py
"""

import time
import logging

from services.weather_service import WeatherService
from data.bigquery_client import BigQueryClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

INTERVAL = 10 * 60  # 10 minutes


def main():
    logger.info("=== Collecte météo outdoor ===")
    ws = WeatherService()
    bq = BigQueryClient()

    while True:
        weather = ws.get_current_weather()
        if weather:
            ok = bq.insert_weather_data(weather)
            logger.info(f"Météo: {weather.city} {weather.temperature_c}°C {weather.weather_description} → BQ {'OK' if ok else 'ERREUR'}")
        else:
            logger.warning("Impossible de récupérer la météo")

        logger.info(f"Prochaine collecte dans {INTERVAL // 60} min...")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Collecte arrêtée (Ctrl+C)")