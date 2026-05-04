import os
from datetime import datetime, timezone
from data.models import SensorReading, WeatherData
from data.bigquery_client import BigQueryClient

def test_connection():
    print("Testing BigQuery Connection...")
    print(f"Project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
    print(f"Dataset: {os.getenv('BQ_DATASET')}")

    client = BigQueryClient()

    # --- Test 1: Insert a fake sensor reading ---
    fake_reading = SensorReading(
        timestamp=datetime.now(timezone.utc),
        device_id="test-device-01",
        temperature_c=22.5,
        humidity_pct=45.0,
        air_quality_index=400,
        motion_detected=False
    )

    print("\nAttempting to insert sensor reading...")
    success = client.insert_sensor_reading(fake_reading)
    if success:
        print("[SUCCESS] Successfully inserted sensor data!")
    else:
        print("[ERROR] Failed to insert sensor data. Check credentials and BigQuery table schema.")

    # --- Test 2: Read back the latest reading ---
    print("\nAttempting to read back the latest sensor data...")
    latest = client.get_latest_sensor_reading("test-device-01")
    if latest:
        print(f"[SUCCESS] Read data! Temperature: {latest.get('temperature_c')}°C")
    else:
        print("[ERROR] Failed to read data or no data found yet.")

if __name__ == "__main__":
    test_connection()
