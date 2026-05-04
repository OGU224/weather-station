"""Routes capteurs — /api/sensors/"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from data.models import SensorReading
from data.bigquery_client import BigQueryClient

bq_client = BigQueryClient()

sensor_bp = Blueprint('sensor_bp', __name__)

@sensor_bp.route('/reading', methods=['POST'])
def post_reading():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON payload provided"}), 400
        
    device_id = data.get("device_id", "m5stack-01")
    
    # Parse timestamp or use current UTC time
    timestamp_str = data.get("timestamp")
    if timestamp_str:
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            timestamp = datetime.now(timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)
        
    reading = SensorReading(
        timestamp=timestamp,
        device_id=device_id,
        temperature_c=data.get("temperature_c", 0.0),
        humidity_pct=data.get("humidity_percent", 0.0),
        air_quality_index=data.get("co2_ppm", 400), # Mapping CO2 to AQI for now
        motion_detected=data.get("motion_detected", False)
    )
    
    success = bq_client.insert_sensor_reading(reading)
    if success:
        return jsonify({"status": "success", "message": "Data saved to BigQuery"}), 201
    else:
        return jsonify({"error": "Failed to save data to BigQuery"}), 500

@sensor_bp.route('/latest', methods=['GET'])
def get_latest():
    device_id = request.args.get('device_id') or None
    latest = bq_client.get_latest_sensor_reading(device_id)
    if latest:
        ts = latest.get("timestamp")
        return jsonify({
            "timestamp": ts.isoformat() if ts else None,
            "device_id": latest.get("device_id"),
            "temperature_c": latest.get("temperature_c"),
            "humidity_pct": latest.get("humidity_pct"),
            "air_quality_index": latest.get("air_quality_index"),
            "air_quality_label": latest.get("air_quality_label"),
            "motion_detected": latest.get("motion_detected"),
        }), 200
    return jsonify({"message": "No data found"}), 404

@sensor_bp.route('/history', methods=['GET'])
def get_history():
    device_id = request.args.get('device_id') or None
    try:
        hours = int(request.args.get('hours', 24))
    except ValueError:
        hours = 24
        
    history = bq_client.get_sensor_history(device_id, hours)
    results = []
    for row in history:
        # Format mapping back to user's expected JSON format if necessary
        results.append({
            "timestamp": row.get("timestamp").isoformat() if row.get("timestamp") else None,
            "device_id": row.get("device_id"),
            "temperature_c": row.get("temperature_c"),
            "humidity_pct": row.get("humidity_pct"),
            "air_quality_index": row.get("air_quality_index"),
            "motion_detected": row.get("motion_detected")
        })
    return jsonify(results), 200
