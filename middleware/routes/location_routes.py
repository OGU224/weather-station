"""Device location routes."""

from flask import Blueprint, jsonify, request

from services.device_location_service import (
    get_device_location,
    get_last_device_location_error,
    update_device_location_from_wifi,
)

location_bp = Blueprint("location_bp", __name__)


@location_bp.route("/wifi", methods=["POST"])
def update_wifi_location():
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id") or request.args.get("device_id")
    access_points = data.get("wifiAccessPoints") or data.get("access_points") or []

    try:
        location = update_device_location_from_wifi(device_id, access_points)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not location:
        return jsonify({
            "ok": False,
            "error": get_last_device_location_error(),
        }), 422

    return jsonify({
        "ok": True,
        "device_id": device_id,
        "location": location,
    }), 200


@location_bp.route("/device/<device_id>", methods=["GET"])
def get_location(device_id):
    location = get_device_location(device_id)
    if not location:
        return jsonify({"error": "No location stored for this device."}), 404
    return jsonify({
        "device_id": device_id,
        "location": location,
    }), 200
