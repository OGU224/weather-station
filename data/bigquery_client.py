"""Client BigQuery.
- insert_sensor_reading(reading) : stocke une lecture capteur
- insert_weather_data(weather) : stocke une donnee meteo
- get_latest_sensor_reading(device_id) : derniere lecture (pour sync au boot)
- get_sensor_history(device_id, hours) : historique capteurs
- get_weather_history(hours) : historique meteo
"""
"""
Client BigQuery â€” insertion et requÃªtes.
"""

import logging
from datetime import datetime, timedelta

from google.cloud import bigquery

from config import GCP_PROJECT, get_bq_table_id, BQ_TABLE_SENSORS, BQ_TABLE_WEATHER

logger = logging.getLogger(__name__)


# Wrap BigQuery inserts and queries used by the middleware.
class BigQueryClient:

    # Initialize the object and its runtime state.
    def __init__(self):
        self.client = bigquery.Client(project=GCP_PROJECT)
        self.sensors_table = get_bq_table_id(BQ_TABLE_SENSORS)
        self.weather_table = get_bq_table_id(BQ_TABLE_WEATHER)
        self._sensor_schema_checked = False

    # Add optional sensor columns when an older BigQuery table is missing them.
    def _ensure_sensor_optional_columns(self):
        if self._sensor_schema_checked:
            return

        try:
            table = self.client.get_table(self.sensors_table)
            field_names = {field.name for field in table.schema}
            new_fields = []
            if "co2_source" not in field_names:
                new_fields.append(bigquery.SchemaField("co2_source", "STRING", mode="NULLABLE"))

            if new_fields:
                table.schema = list(table.schema) + new_fields
                self.client.update_table(table, ["schema"])
        except Exception as e:
            logger.warning(f"Could not update sensor table schema: {e}")
        finally:
            self._sensor_schema_checked = True

    # Insert one indoor sensor reading into BigQuery.
    def insert_sensor_reading(self, reading):
        try:
            self._ensure_sensor_optional_columns()
            row = reading.to_dict()
            errors = self.client.insert_rows_json(self.sensors_table, [row])
            if errors and "co2_source" in row:
                # Keep the reading flowing even if an older BigQuery table has not been migrated yet.
                row_without_source = dict(row)
                row_without_source.pop("co2_source", None)
                errors = self.client.insert_rows_json(self.sensors_table, [row_without_source])
            if errors:
                logger.error(f"Erreur insertion sensor: {errors}")
                return False
            return True
        except Exception as e:
            logger.error(f"Exception BigQuery: {e}")
            return False

    # Insert one outdoor weather snapshot into BigQuery.
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

    # Return the newest sensor reading, optionally for one device.
    def get_latest_sensor_reading(self, device_id=None):
        where_clause = "WHERE device_id = @device_id" if device_id else ""
        query = f"""
            SELECT * FROM `{self.sensors_table}`
            {where_clause}
            ORDER BY timestamp DESC LIMIT 1
        """
        query_parameters = []
        if device_id:
            query_parameters.append(bigquery.ScalarQueryParameter("device_id", "STRING", device_id))
        job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
        try:
            for row in self.client.query(query, job_config=job_config).result():
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Query error: {e}")
            return None

    # Return recent sensor readings for history and assistant context.
    def get_sensor_history(self, device_id=None, hours=24):
        device_filter = "AND device_id = @device_id" if device_id else ""
        since = datetime.utcnow() - timedelta(hours=hours)
        query = f"""
            SELECT * FROM `{self.sensors_table}`
            WHERE timestamp >= @since {device_filter}
            ORDER BY timestamp ASC
        """
        query_parameters = [bigquery.ScalarQueryParameter("since", "TIMESTAMP", since)]
        if device_id:
            query_parameters.append(bigquery.ScalarQueryParameter("device_id", "STRING", device_id))
        job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
        try:
            return [dict(row) for row in self.client.query(query, job_config=job_config).result()]
        except Exception as e:
            logger.error(f"Query error: {e}")
            return []

    # Return recent stored outdoor weather history.
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
