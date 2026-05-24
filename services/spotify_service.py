"""Spotify playback service for the smart-home morning routine."""

import base64
import os
import secrets
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_SCOPES = "user-read-playback-state user-modify-playback-state"


def _get_required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not configured.")
    return value


def _client_auth_header():
    client_id = _get_required_env("SPOTIFY_CLIENT_ID")
    client_secret = _get_required_env("SPOTIFY_CLIENT_SECRET")
    token = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def get_authorization_url():
    """Return a Spotify consent URL for the user to open once."""
    client_id = _get_required_env("SPOTIFY_CLIENT_ID")
    redirect_uri = _get_required_env("SPOTIFY_REDIRECT_URI")
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SPOTIFY_SCOPES,
        "state": state,
    }
    return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code):
    """Exchange OAuth code for tokens. Paste refresh_token into .env."""
    redirect_uri = _get_required_env("SPOTIFY_REDIRECT_URI")
    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers=_client_auth_header(),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token():
    refresh_token = _get_required_env("SPOTIFY_REFRESH_TOKEN")
    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers=_client_auth_header(),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _spotify_headers():
    return {
        "Authorization": f"Bearer {refresh_access_token()}",
        "Content-Type": "application/json",
    }


def get_devices():
    response = requests.get(
        f"{SPOTIFY_API_BASE}/me/player/devices",
        headers=_spotify_headers(),
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("devices", [])


def _playlist_for_mood(mood, temperature_c=None):
    mood_text = str(mood or "").lower()
    try:
        temp = float(temperature_c) if temperature_c is not None else None
    except (TypeError, ValueError):
        temp = None

    if "rain" in mood_text or "drizzle" in mood_text or "storm" in mood_text:
        return os.getenv("SPOTIFY_MOOD_RAIN_URI") or os.getenv("SPOTIFY_MOOD_DEFAULT_URI", "")
    if temp is not None and temp >= 24:
        return os.getenv("SPOTIFY_MOOD_HOT_URI") or os.getenv("SPOTIFY_MOOD_CLEAR_URI") or os.getenv("SPOTIFY_MOOD_DEFAULT_URI", "")
    if temp is not None and temp <= 10:
        return os.getenv("SPOTIFY_MOOD_COLD_URI") or os.getenv("SPOTIFY_MOOD_CLOUD_URI") or os.getenv("SPOTIFY_MOOD_DEFAULT_URI", "")
    if "clear" in mood_text or "sun" in mood_text:
        return os.getenv("SPOTIFY_MOOD_CLEAR_URI") or os.getenv("SPOTIFY_MOOD_DEFAULT_URI", "")
    if "cloud" in mood_text:
        return os.getenv("SPOTIFY_MOOD_CLOUD_URI") or os.getenv("SPOTIFY_MOOD_DEFAULT_URI", "")
    return os.getenv("SPOTIFY_MOOD_DEFAULT_URI", "")


def play_mood(mood=None, temperature_c=None, device_id=None):
    """Start Spotify playback for a weather mood on an active Spotify device."""
    uri = _playlist_for_mood(mood, temperature_c=temperature_c)
    if not uri:
        raise RuntimeError("No Spotify mood URI is configured.")

    payload = {}
    if uri.startswith("spotify:track:"):
        payload["uris"] = [uri]
    else:
        payload["context_uri"] = uri

    target_device = device_id or os.getenv("SPOTIFY_DEVICE_ID", "").strip()
    params = {"device_id": target_device} if target_device else None
    response = requests.put(
        f"{SPOTIFY_API_BASE}/me/player/play",
        headers=_spotify_headers(),
        params=params,
        json=payload,
        timeout=15,
    )

    if response.status_code == 404:
        raise RuntimeError("No active Spotify device found. Open Spotify on your phone or laptop first.")
    if response.status_code == 403:
        raise RuntimeError("Spotify playback requires Premium and playback-control permission.")
    response.raise_for_status()
    return {
        "success": True,
        "uri": uri,
        "mood": mood,
        "device_id": target_device or "active-device",
    }
