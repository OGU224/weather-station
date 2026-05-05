import os
import sys

import pandas as pd
import plotly.graph_objects as go
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


def _fmt(value, decimals=1):
    if pd.isna(value):
        return "--"
    return f"{value:.{decimals}f}"


def _comfort_score(df: pd.DataFrame) -> tuple[int, str]:
    if df.empty:
        return 0, "No indoor data available."

    score = 100
    notes = []

    if "temperature_c" in df.columns and df["temperature_c"].notna().any():
        avg_temp = df["temperature_c"].mean()
        if avg_temp < 20:
            score -= min(25, int((20 - avg_temp) * 6))
            notes.append("temperature was cooler than the comfort range")
        elif avg_temp > 24:
            score -= min(25, int((avg_temp - 24) * 6))
            notes.append("temperature was warmer than the comfort range")

    if "humidity_pct" in df.columns and df["humidity_pct"].notna().any():
        low_humidity_share = (df["humidity_pct"] < 40).mean()
        high_humidity_share = (df["humidity_pct"] > 60).mean()
        if low_humidity_share > 0:
            score -= min(35, int(low_humidity_share * 45))
            notes.append("humidity dipped below 40%")
        if high_humidity_share > 0:
            score -= min(25, int(high_humidity_share * 35))
            notes.append("humidity rose above 60%")

    if "air_quality_index" in df.columns and df["air_quality_index"].notna().any():
        poor_air_share = (df["air_quality_index"] >= 100).mean()
        if poor_air_share > 0:
            score -= min(30, int(poor_air_share * 35))
            notes.append("air quality readings were elevated")

    score = max(0, min(100, score))
    if score >= 80:
        label = "Comfortable conditions overall."
    elif score >= 60:
        label = "Mostly acceptable, with a few comfort issues."
    else:
        label = "Comfort issues were frequent in this period."

    if notes:
        label += " Main signal: " + ", ".join(notes[:2]) + "."
    return score, label


def _motion_by_hour_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if df.empty or "timestamp" not in df.columns or "motion_detected" not in df.columns:
        fig.add_annotation(
            text="No motion data available",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(color="#94a3b8", size=14),
        )
    else:
        motion_df = df[df["motion_detected"] == True].copy()
        if not motion_df.empty:
            motion_df["hour"] = motion_df["timestamp"].dt.floor("h")
            counts = motion_df.groupby("hour").size().reset_index(name="events")
            fig.add_trace(go.Bar(
                x=counts["hour"],
                y=counts["events"],
                marker_color="#fb923c",
                name="Motion events",
            ))
        else:
            fig.add_annotation(
                text="No motion detected in this period",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(color="#94a3b8", size=14),
            )

    fig.update_layout(
        title="Motion Events By Hour",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="Events",
        xaxis_title="",
        margin=dict(l=0, r=0, t=40, b=0),
        height=260,
    )
    return fig


def _render_insights(sensor_df: pd.DataFrame):
    if sensor_df.empty:
        return

    st.markdown("### Indoor Insights")
    score, recommendation = _comfort_score(sensor_df)

    temp_avg = sensor_df["temperature_c"].mean() if "temperature_c" in sensor_df.columns else float("nan")
    hum_avg = sensor_df["humidity_pct"].mean() if "humidity_pct" in sensor_df.columns else float("nan")
    low_humidity_count = int((sensor_df["humidity_pct"] < 40).sum()) if "humidity_pct" in sensor_df.columns else 0
    motion_count = int((sensor_df["motion_detected"] == True).sum()) if "motion_detected" in sensor_df.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Comfort Score", f"{score}/100")
    m2.metric("Avg Temp", f"{_fmt(temp_avg)} C")
    m3.metric("Avg Humidity", f"{_fmt(hum_avg)}%")
    m4.metric("Motion Events", motion_count)

    if low_humidity_count:
        st.warning(f"Humidity was below 40% for {low_humidity_count} reading(s) in this period.")

    if "humidity_pct" in sensor_df.columns and sensor_df["humidity_pct"].notna().any():
        lowest = sensor_df.loc[sensor_df["humidity_pct"].idxmin()]
        lowest_time = lowest["timestamp"].strftime("%Y-%m-%d %H:%M")
        st.caption(f"Lowest humidity: {_fmt(lowest['humidity_pct'])}% at {lowest_time}.")

    st.info(recommendation)

    st.plotly_chart(_motion_by_hour_chart(sensor_df), use_container_width=True)


def render():
    """Render the history page."""
    st.title("Historical Data")
    st.caption("Review comfort, motion, and weather trends from BigQuery.")

    col_ctrl1, col_ctrl2 = st.columns([2, 2])
    with col_ctrl1:
        selected_range = st.selectbox("Time Range", list(TIME_OPTIONS.keys()), index=2)
    with col_ctrl2:
        device_id = st.text_input("Device ID filter", value="", placeholder="All devices")

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

        _render_insights(sensor_df)

        tab_temp, tab_humidity, tab_air = st.tabs(["Temperature", "Humidity", "Air Quality"])
        with tab_temp:
            st.plotly_chart(
                temperature_chart(sensor_df, indoor_col="temperature_c", title="Indoor Temperature"),
                use_container_width=True,
            )
        with tab_humidity:
            st.plotly_chart(
                humidity_chart(sensor_df, col="humidity_pct", title="Indoor Humidity"),
                use_container_width=True,
            )
        with tab_air:
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

    with st.expander("Outdoor collection controls"):
        st.caption("Use this for a manual weather snapshot. For regular data, run collect_data.py.")
        if st.button("Save Outdoor Now", use_container_width=True):
            ok, message = _store_current_weather_snapshot()
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    if not weather_df.empty:
        if weather_source == "bigquery":
            st.caption("Outdoor history loaded directly from BigQuery because the middleware was unreachable.")

        tab_out_temp, tab_out_humidity = st.tabs(["Temperature", "Humidity"])
        with tab_out_temp:
            st.plotly_chart(
                temperature_chart(weather_df, indoor_col="temperature_c", title="Outdoor Temperature"),
                use_container_width=True,
            )
        with tab_out_humidity:
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

    if st.toggle("Show raw sensor rows", value=False):
        if sensor_df.empty:
            st.write("No data.")
            return
        display_cols = [
            c for c in [
                "timestamp",
                "device_id",
                "temperature_c",
                "humidity_pct",
                "air_quality_index",
                "motion_detected",
            ]
            if c in sensor_df.columns
        ]
        st.dataframe(sensor_df[display_cols].sort_values("timestamp", ascending=False), use_container_width=True)
