import os
import sys

import pandas as pd
import requests
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from components.charts import air_quality_chart, humidity_chart, temperature_chart

MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "http://127.0.0.1:5000")

TIME_OPTIONS = {
    "Last 6 hours": 6,
    "Last 12 hours": 12,
    "Last 24 hours": 24,
    "Last 48 hours": 48,
    "Last 7 days": 168,
}


def _fetch(path: str, params: dict = None):
    """Fetch JSON from the Flask middleware. Returns None on failure."""
    try:
        resp = requests.get(f"{MIDDLEWARE_URL}{path}", params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        pass
    return None


def _rows_to_sensor_payload(rows):
    results = []
    for row in rows:
        ts = row.get("timestamp")
        results.append({
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else ts,
            "device_id": row.get("device_id"),
            "temperature_c": row.get("temperature_c"),
            "humidity_pct": row.get("humidity_pct"),
            "air_quality_index": row.get("air_quality_index"),
            "motion_detected": row.get("motion_detected"),
        })
    return results


def _fetch_sensor_history(device_id: str, hours: int):
    """Use the middleware first, then fall back to BigQuery directly."""
    device_id = device_id.strip() or None
    params = {"hours": hours}
    if device_id:
        params["device_id"] = device_id

    data = _fetch("/api/sensors/history", params=params)
    if data:
        return data, "middleware"

    try:
        from data.bigquery_client import BigQueryClient

        rows = BigQueryClient().get_sensor_history(device_id=device_id, hours=hours)
        return _rows_to_sensor_payload(rows), "bigquery"
    except Exception as exc:
        st.session_state["sensor_history_error"] = str(exc)
        return [], "unavailable"


def _rows_to_weather_payload(rows):
    results = []
    for row in rows:
        ts = row.get("timestamp")
        results.append({
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else ts,
            "temperature_c": row.get("temperature_c"),
            "feels_like_c": row.get("feels_like_c"),
            "humidity_pct": row.get("humidity_pct"),
            "wind_speed_ms": row.get("wind_speed_ms"),
            "weather_main": row.get("weather_main"),
            "weather_description": row.get("weather_description"),
            "weather_icon": row.get("weather_icon"),
            "city": row.get("city"),
        })
    return results


def _fetch_weather_history(hours: int):
    """Use the middleware first, then fall back to BigQuery directly."""
    data = _fetch("/api/weather/history", params={"hours": hours})
    if data:
        return data, "middleware"

    try:
        from data.bigquery_client import BigQueryClient

        rows = BigQueryClient().get_weather_history(hours=hours)
        return _rows_to_weather_payload(rows), "bigquery"
    except Exception as exc:
        st.session_state["weather_history_error"] = str(exc)
        return [], "unavailable"


def _store_current_weather_snapshot():
    """Store one current outdoor weather reading for history charts."""
    try:
        resp = requests.get(f"{MIDDLEWARE_URL}/api/weather/current", params={"store": "true"}, timeout=10)
        if resp.status_code == 200:
            return True, "Stored current outdoor weather through the middleware."
    except requests.RequestException:
        pass

    try:
        from data.bigquery_client import BigQueryClient
        from services.weather_service import WeatherService

        service = WeatherService()
        weather = service.get_current_weather()
        if not weather:
            return False, f"OpenWeatherMap did not return current weather: {service.last_error}"

        ok = BigQueryClient().insert_weather_data(weather)
        if ok:
            return True, "Stored current outdoor weather directly in BigQuery."
        return False, "BigQuery rejected the weather row. Check credentials and table schema."
    except Exception as exc:
        return False, f"Could not store outdoor weather: {exc}"


def _to_df(data: list, time_col: str = "timestamp") -> pd.DataFrame:
    """Convert API list response to DataFrame with parsed timestamps."""
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    # Backward compatibility for older API payloads.
    df = df.rename(columns={
        "humidity_percent": "humidity_pct",
        "co2_ppm": "air_quality_index",
    })

    for col in ["temperature_c", "humidity_pct", "air_quality_index", "feels_like_c", "wind_speed_ms"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if time_col in df.columns:
        df[time_col] = pd.to_datetime(df[time_col], utc=True, errors="coerce")
        df = df.dropna(subset=[time_col]).sort_values(time_col)
    return df


def render():
    """Render the history page."""
    st.title("Historical Data")

    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 1.6])
    with col_ctrl1:
        selected_range = st.selectbox("Time Range", list(TIME_OPTIONS.keys()), index=2)
    with col_ctrl2:
        device_id = st.text_input("Device ID filter", value="", placeholder="All devices")
    with col_ctrl3:
        st.write("")
        st.write("")
        if st.button("Save Outdoor Now", use_container_width=True):
            ok, message = _store_current_weather_snapshot()
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    hours = TIME_OPTIONS[selected_range]

    with st.spinner("Loading historical data from BigQuery..."):
        sensor_data, sensor_source = _fetch_sensor_history(device_id=device_id, hours=hours)
        weather_data, weather_source = _fetch_weather_history(hours=hours)

    sensor_df = _to_df(sensor_data or [])
    weather_df = _to_df(weather_data or [])

    if sensor_df.empty and weather_df.empty:
        st.warning(
            "No historical data found. Make sure the middleware is running and "
            "sensors have been sending data."
        )
        return

    st.markdown("### Indoor History")
    st.caption(f"Showing {'all devices' if not device_id.strip() else device_id.strip()}.")

    if not sensor_df.empty:
        if sensor_source == "bigquery":
            st.caption("Indoor history loaded directly from BigQuery because the middleware was unreachable.")

        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(
                temperature_chart(sensor_df, indoor_col="temperature_c", title="Indoor Temperature"),
                use_container_width=True,
            )

        with col2:
            st.plotly_chart(
                humidity_chart(sensor_df, col="humidity_pct", title="Indoor Humidity"),
                use_container_width=True,
            )

        st.plotly_chart(
            air_quality_chart(sensor_df, col="air_quality_index", title="Air Quality Index"),
            use_container_width=True,
        )

        if "motion_detected" in sensor_df.columns:
            motion_df = sensor_df[sensor_df["motion_detected"] == True]
            if not motion_df.empty:
                st.markdown(f"**Motion detected {len(motion_df)} time(s)** in this period.")
            else:
                st.markdown("**No motion detected** in this period.")
    else:
        error = st.session_state.get("sensor_history_error")
        if error:
            st.info(f"No indoor sensor data available. Middleware is unreachable and direct BigQuery failed: {error}")
        else:
            st.info("No indoor sensor data available for this period.")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### Outdoor History")

    if not weather_df.empty:
        if weather_source == "bigquery":
            st.caption("Outdoor history loaded directly from BigQuery because the middleware was unreachable.")

        col3, col4 = st.columns(2)

        with col3:
            st.plotly_chart(
                temperature_chart(weather_df, indoor_col="temperature_c", title="Outdoor Temperature"),
                use_container_width=True,
            )

        with col4:
            st.plotly_chart(
                humidity_chart(weather_df, col="humidity_pct", title="Outdoor Humidity"),
                use_container_width=True,
            )
    else:
        error = st.session_state.get("weather_history_error")
        if error:
            st.info(f"No outdoor weather history available. Middleware is unreachable and direct BigQuery failed: {error}")
        else:
            st.info(
                "No outdoor weather history yet. Use Save Outdoor Now to write the "
                "current OpenWeatherMap reading into BigQuery."
            )

    with st.expander("View raw sensor data"):
        if not sensor_df.empty:
            display_cols = [
                c for c in [
                    "timestamp",
                    "temperature_c",
                    "humidity_pct",
                    "air_quality_index",
                    "motion_detected",
                ]
                if c in sensor_df.columns
            ]
            st.dataframe(sensor_df[display_cols].sort_values("timestamp", ascending=False), use_container_width=True)
        else:
            st.write("No data.")
