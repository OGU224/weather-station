"""Periodically store outdoor weather snapshots in BigQuery.

Usage:
    python collect_data.py

Configuration:
    OUTDOOR_COLLECTION_INTERVAL_SECONDS=600
"""

import logging
import os
import time
from datetime import datetime

from dotenv import load_dotenv

from data.bigquery_client import BigQueryClient
from services.weather_service import WeatherService

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 10 * 60
MIN_INTERVAL_SECONDS = 60


def _interval_seconds() -> int:
    try:
        configured = int(os.getenv("OUTDOOR_COLLECTION_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS))
    except ValueError:
        configured = DEFAULT_INTERVAL_SECONDS
    return max(MIN_INTERVAL_SECONDS, configured)


def _store_snapshot(weather_service: WeatherService, bq_client: BigQueryClient) -> bool:
    weather = weather_service.get_current_weather()
    if not weather:
        logger.warning("Outdoor weather unavailable: %s", weather_service.last_error or "unknown error")
        return False

    ok = bq_client.insert_weather_data(weather)
    status = "OK" if ok else "FAILED"
    logger.info(
        "Outdoor snapshot %s | %s %.1f C, %s, wind %.1f m/s",
        status,
        weather.city,
        weather.temperature_c,
        weather.weather_description,
        weather.wind_speed_ms,
    )
    return ok


def main():
    interval = _interval_seconds()
    weather_service = WeatherService()
    bq_client = BigQueryClient()

    logger.info("Outdoor collector started.")
    logger.info("Interval: %s seconds (%s min)", interval, round(interval / 60, 1))
    logger.info("First snapshot runs immediately.")

    while True:
        started = datetime.now()
        _store_snapshot(weather_service, bq_client)

        elapsed = (datetime.now() - started).total_seconds()
        sleep_for = max(0, interval - elapsed)
        logger.info("Next outdoor snapshot in %.1f min.", sleep_for / 60)
        time.sleep(sleep_for)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Outdoor collector stopped.")
