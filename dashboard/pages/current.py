import os
import sys
from dataclasses import asdict
from datetime import datetime

import requests
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from components.charts import forecast_cards, metric_card, weather_emoji

MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "http://127.0.0.1:5000")
HUMIDITY_ALERT = 40


def _fetch(path: str, params: dict = None):
    """Fetch JSON from the Flask middleware. Returns None on failure."""
    try:
        resp = requests.get(f"{MIDDLEWARE_URL}{path}", params=params, timeout=8)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        pass
    return None


def _row_to_sensor_payload(row):
    if not row:
        return None
    ts = row.get("timestamp")
    return {
        "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else ts,
        "device_id": row.get("device_id"),
        "temperature_c": row.get("temperature_c"),
        "humidity_pct": row.get("humidity_pct"),
        "air_quality_index": row.get("air_quality_index"),
        "air_quality_label": row.get("air_quality_label"),
        "motion_detected": row.get("motion_detected"),
    }


def _fetch_latest_sensor():
    """Use the middleware first, then fall back to BigQuery directly."""
    sensor = _fetch("/api/sensors/latest")
    if sensor:
        return sensor, "middleware"

    try:
        from data.bigquery_client import BigQueryClient

        row = BigQueryClient().get_latest_sensor_reading()
        return _row_to_sensor_payload(row), "bigquery"
    except Exception as exc:
        st.session_state["sensor_error"] = str(exc)
        return None, "unavailable"


def _fetch_current_weather():
    """Use the middleware first, then fall back to OpenWeatherMap directly."""
    weather = _fetch("/api/weather/current")
    if weather:
        st.session_state.pop("weather_error", None)
        return weather, "middleware"

    try:
        from services.weather_service import WeatherService

        service = WeatherService()
        weather_data = service.get_current_weather()
        if weather_data:
            st.session_state.pop("weather_error", None)
            return weather_data.to_dict(), "openweathermap"
        if service.last_error:
            st.session_state["weather_error"] = service.last_error
    except Exception as exc:
        st.session_state["weather_error"] = str(exc)
    return None, "unavailable"


def _fetch_forecast(days: int = 5):
    """Use the middleware first, then fall back to OpenWeatherMap directly."""
    forecast = _fetch("/api/weather/forecast", params={"days": days})
    if forecast:
        st.session_state.pop("forecast_error", None)
        return forecast, "middleware"

    try:
        from services.weather_service import WeatherService

        service = WeatherService()
        forecast_data = service.get_forecast(days=days)
        if forecast_data:
            st.session_state.pop("forecast_error", None)
            return [asdict(day) for day in forecast_data], "openweathermap"
        if service.last_error:
            st.session_state["forecast_error"] = service.last_error
    except Exception as exc:
        st.session_state["forecast_error"] = str(exc)
    return [], "unavailable"


def _number(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_number(value, decimals=1):
    numeric = _number(value)
    if numeric is None:
        return "--"
    return f"{numeric:.{decimals}f}"


def _aqi_label(aqi) -> tuple[str, str]:
    """Return (label, color) for an air quality value."""
    value = _number(aqi)
    if value is None:
        return "--", "#94a3b8"
    if value < 50:
        return "Good", "#34d399"
    if value < 100:
        return "Moderate", "#fbbf24"
    return "Poor", "#f87171"


def render():
    """Render the real-time dashboard page."""
    st.title("Real-Time Conditions")

    with st.spinner("Fetching latest data..."):
        sensor, sensor_source = _fetch_latest_sensor()
        weather, weather_source = _fetch_current_weather()
        forecast, forecast_source = _fetch_forecast()

    if sensor:
        humidity = _number(sensor.get("humidity_pct"), 100)
        aqi = _number(sensor.get("air_quality_index"), 0)
        aqi_label, _ = _aqi_label(aqi)

        if humidity is not None and humidity < HUMIDITY_ALERT:
            st.error(
                f"Low humidity alert: indoor humidity is {humidity:.0f}%, "
                f"below the {HUMIDITY_ALERT}% threshold."
            )
        if aqi_label == "Poor":
            st.warning(f"Poor air quality: AQI is {aqi:.0f}. Ventilate the room.")

    st.markdown("### Indoor")
    c1, c2, c3, c4 = st.columns(4)

    if sensor:
        temp_in = sensor.get("temperature_c")
        hum_in = sensor.get("humidity_pct")
        aqi_val = sensor.get("air_quality_index")
        motion = bool(sensor.get("motion_detected", False))
        aqi_lbl, aqi_color = _aqi_label(aqi_val)
        hum_numeric = _number(hum_in)
        hum_color = "#f87171" if hum_numeric is not None and hum_numeric < HUMIDITY_ALERT else "#34d399"

        c1.markdown(metric_card("Temperature", _format_number(temp_in), "C", icon="Temp"), unsafe_allow_html=True)
        c2.markdown(metric_card("Humidity", _format_number(hum_in, 0), "%", icon="H2O", color=hum_color), unsafe_allow_html=True)
        c3.markdown(metric_card("Air Quality", aqi_lbl, f"({_format_number(aqi_val, 0)})", icon="AQI", color=aqi_color), unsafe_allow_html=True)
        c4.markdown(metric_card("Motion", "Detected" if motion else "None", "", icon="Move", color="#fb923c" if motion else "#94a3b8"), unsafe_allow_html=True)
    else:
        for c in [c1, c2, c3, c4]:
            c.markdown(metric_card("--", "--", "", icon="No data", color="#64748b"), unsafe_allow_html=True)
        error = st.session_state.get("sensor_error")
        if error:
            st.caption(f"Indoor data unavailable. Middleware is unreachable and direct BigQuery failed: {error}")
        else:
            st.caption("Indoor data unavailable. Check the middleware or BigQuery credentials.")

    if sensor and sensor_source == "bigquery":
        st.caption("Indoor data loaded directly from BigQuery because the middleware was unreachable.")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### Outdoor")
    o1, o2, o3, o4 = st.columns(4)

    if weather:
        if weather_source == "openweathermap":
            st.caption("Outdoor data loaded directly from OpenWeatherMap because the middleware was unreachable.")

        temp_out = weather.get("temperature_c")
        feels = weather.get("feels_like_c")
        wind = weather.get("wind_speed_ms")
        w_main = weather.get("weather_main", "--")
        w_desc = weather.get("weather_description", "").capitalize()
        w_icon = weather.get("weather_icon", "")
        icon_url = f"https://openweathermap.org/img/wn/{w_icon}@2x.png" if w_icon else ""
        fallback_label = weather_emoji(w_main)

        o1.markdown(metric_card("Temperature", _format_number(temp_out), "C", icon="Temp", color="#fb923c"), unsafe_allow_html=True)
        o2.markdown(metric_card("Feels Like", _format_number(feels), "C", icon="Feels", color="#fb923c"), unsafe_allow_html=True)
        o3.markdown(metric_card("Wind", _format_number(wind), "m/s", icon="Wind"), unsafe_allow_html=True)

        with o4:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #1e293b, #0f172a);
                border: 1px solid #334155;
                border-radius: 14px;
                padding: 10px;
                text-align: center;
                min-height: 130px;
                display: flex; flex-direction: column; justify-content: center;
            ">
                <div style="font-size:0.75rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.08em;">Conditions</div>
                {"<img src='" + icon_url + "' width='44' style='margin:4px auto;display:block;'/>" if icon_url else f"<div style='font-size:1rem;color:#e2e8f0;margin:12px 0;'>{fallback_label}</div>"}
                <div style="font-size:0.9rem;color:#e2e8f0;">{w_desc or fallback_label}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        for c in [o1, o2, o3, o4]:
            c.markdown(metric_card("--", "--", "", icon="No data", color="#64748b"), unsafe_allow_html=True)
        error = st.session_state.get("weather_error")
        if error:
            st.caption(f"Outdoor weather unavailable. Middleware is unreachable and direct OpenWeatherMap failed: {error}")
        else:
            st.caption("Outdoor weather unavailable. Check OWM_API_KEY in .env.")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 5-Day Forecast")
    if forecast and isinstance(forecast, list):
        if forecast_source == "openweathermap":
            st.caption("Forecast loaded directly from OpenWeatherMap because the middleware was unreachable.")
        forecast_cards(forecast)
    else:
        error = st.session_state.get("forecast_error")
        if error:
            st.info(f"Forecast unavailable. Middleware is unreachable and direct OpenWeatherMap failed: {error}")
        else:
            st.info("Forecast unavailable. Add OWM_API_KEY to your .env file.")

    with st.expander("Data sources"):
        st.write({
            "indoor": sensor_source,
            "outdoor": weather_source,
            "forecast": forecast_source,
            "outdoor_city": weather.get("city") if weather else None,
            "outdoor_error": st.session_state.get("weather_error"),
            "forecast_error": st.session_state.get("forecast_error"),
        })

    st.markdown(
        f"<p style='color:#475569; font-size:0.75rem; margin-top: 2rem;'>"
        f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}</p>",
        unsafe_allow_html=True,
    )
