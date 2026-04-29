"""Client BigQuery.
- insert_sensor_reading(reading) : stocke une lecture capteur
- insert_weather_data(weather) : stocke une donnee meteo
- get_latest_sensor_reading(device_id) : derniere lecture (pour sync au boot)
- get_sensor_history(device_id, hours) : historique capteurs
- get_weather_history(hours) : historique meteo
"""
"""
Client BigQuery — insertion et requêtes.
"""

import logging
from datetime import datetime, timedelta

from google.cloud import bigquery

from config import GCP_PROJECT, get_bq_table_id, BQ_TABLE_SENSORS, BQ_TABLE_WEATHER

logger = logging.getLogger(__name__)


class BigQueryClient:

    def __init__(self):
        self.client = bigquery.Client(project=GCP_PROJECT)
        self.sensors_table = get_bq_table_id(BQ_TABLE_SENSORS)
        self.weather_table = get_bq_table_id(BQ_TABLE_WEATHER)

    def insert_sensor_reading(self, reading):
        try:
            errors = self.client.insert_rows_json(self.sensors_table, [reading.to_dict()])
            if errors:
                logger.error(f"Erreur insertion sensor: {errors}")
                return False
            return True
        except Exception as e:
            logger.error(f"Exception BigQuery: {e}")
            return False

    def insert_weather_data(self, weather):
        try:
            errors = self.client.insert_rows_json(self.weather_table, [weather.to_dict()])
            if errors:
                logger.error(f"Erreur insertion weather: {errors}")
                return False
            return True
        except Exception as e:
            logger.error(f"Exception BigQuery: {e}")
            return False

    def get_latest_sensor_reading(self, device_id="m5stack-01"):
        query = f"""
            SELECT * FROM `{self.sensors_table}`
            WHERE device_id = @device_id
            ORDER BY timestamp DESC LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("device_id", "STRING", device_id)]
        )
        try:
            for row in self.client.query(query, job_config=job_config).result():
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Query error: {e}")
            return None

    def get_sensor_history(self, device_id="m5stack-01", hours=24):
        query = f"""
            SELECT * FROM `{self.sensors_table}`
            WHERE device_id = @device_id AND timestamp >= @since
            ORDER BY timestamp ASC
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("device_id", "STRING", device_id),
                bigquery.ScalarQueryParameter("since", "TIMESTAMP", since),
            ]
        )
        try:
            return [dict(row) for row in self.client.query(query, job_config=job_config).result()]
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []

    def get_weather_history(self, hours=24):
        query = f"""
            SELECT * FROM `{self.weather_table}`
            WHERE timestamp >= @since
            ORDER BY timestamp ASC
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("since", "TIMESTAMP", since)]
        )
        try:
            return [dict(row) for row in self.client.query(query, job_config=job_config).result()]
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []