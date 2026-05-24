"""Music routes for smart-home Spotify playback."""

from flask import Blueprint, jsonify, request

from services.spotify_service import (
    exchange_code_for_token,
    get_authorization_url,
    get_devices,
    play_mood,
)

music_bp = Blueprint("music_bp", __name__)


@music_bp.route("/spotify/auth-url", methods=["GET"])
def spotify_auth_url():
    try:
        return jsonify({"auth_url": get_authorization_url()}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@music_bp.route("/spotify/callback", methods=["GET"])
def spotify_callback():
    code = request.args.get("code", "")
    if not code:
        return jsonify({"error": "Missing Spotify code."}), 400

    try:
        token_data = exchange_code_for_token(code)
        return jsonify({
            "message": "Copy refresh_token into your .env as SPOTIFY_REFRESH_TOKEN, then restart Flask.",
            "refresh_token": token_data.get("refresh_token"),
            "scope": token_data.get("scope"),
            "expires_in": token_data.get("expires_in"),
        }), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@music_bp.route("/spotify/devices", methods=["GET"])
def spotify_devices():
    try:
        devices = get_devices()
        return jsonify({"devices": devices}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@music_bp.route("/play-mood", methods=["GET", "POST"])
def play_weather_mood():
    data = request.get_json(silent=True) or {}
    mood = data.get("mood") or request.args.get("mood") or "default"
    temperature = data.get("temperature_c") or request.args.get("temperature_c")
    device_id = data.get("device_id") or request.args.get("device_id")

    try:
        result = play_mood(mood=mood, temperature_c=temperature, device_id=device_id)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
