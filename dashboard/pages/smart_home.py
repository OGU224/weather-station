import os
import sys
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, REPO_ROOT)

MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "http://127.0.0.1:5000")


def _fetch(path: str, params: dict = None):
    try:
        response = requests.get(f"{MIDDLEWARE_URL}{path}", params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return None


def _post(path: str, payload: dict = None, timeout=18):
    response = requests.post(f"{MIDDLEWARE_URL}{path}", json=payload or {}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _sensor_history(hours=24):
    data = _fetch("/api/sensors/history", params={"hours": hours})
    if data:
        return data
    try:
        from data.bigquery_client import BigQueryClient

        rows = BigQueryClient().get_sensor_history(hours=hours)
        results = []
        for row in rows:
            ts = row.get("timestamp")
            results.append({
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else ts,
                "device_id": row.get("device_id"),
                "temperature_c": row.get("temperature_c"),
                "humidity_pct": row.get("humidity_pct"),
                "air_quality_index": row.get("air_quality_index"),
                "co2_source": row.get("co2_source"),
                "motion_detected": row.get("motion_detected"),
            })
        return results
    except Exception:
        return []


def _latest_sensor():
    data = _fetch("/api/sensors/latest")
    if data:
        return data
    try:
        from data.bigquery_client import BigQueryClient

        row = BigQueryClient().get_latest_sensor_reading()
        if not row:
            return None
        ts = row.get("timestamp")
        return {
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else ts,
            "device_id": row.get("device_id"),
            "temperature_c": row.get("temperature_c"),
            "humidity_pct": row.get("humidity_pct"),
            "air_quality_index": row.get("air_quality_index"),
            "co2_source": row.get("co2_source"),
            "motion_detected": row.get("motion_detected"),
        }
    except Exception:
        return None


def _current_weather():
    data = _fetch("/api/weather/current")
    if data:
        return data
    try:
        from services.weather_service import WeatherService

        weather = WeatherService().get_current_weather()
        return weather.to_dict() if weather else None
    except Exception:
        return None


def _forecast(days=3):
    data = _fetch("/api/weather/forecast", params={"days": days})
    if data:
        return data
    try:
        from dataclasses import asdict
        from services.weather_service import WeatherService

        return [asdict(day) for day in WeatherService().get_forecast(days=days)]
    except Exception:
        return []


def _spotify_devices():
    data = _fetch("/api/music/spotify/devices")
    return (data or {}).get("devices", [])


def _to_df(rows):
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in ["temperature_c", "humidity_pct", "air_quality_index"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    return df


def _num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fmt(value, decimals=1, suffix=""):
    value = _num(value)
    if value is None:
        return "--"
    return f"{value:.{decimals}f}{suffix}"


def _age_label(timestamp_value):
    if not timestamp_value:
        return "--"
    try:
        ts = pd.to_datetime(timestamp_value, utc=True)
    except Exception:
        return "--"
    if pd.isna(ts):
        return "--"
    age_minutes = max(0, (datetime.now(timezone.utc) - ts.to_pydatetime()).total_seconds() / 60)
    if age_minutes < 1:
        return "now"
    if age_minutes < 60:
        return f"{int(age_minutes)}m ago"
    return f"{round(age_minutes / 60, 1)}h ago"


def _comfort_score(latest, history_df):
    score = 100
    reasons = []
    temp = _num((latest or {}).get("temperature_c"))
    hum = _num((latest or {}).get("humidity_pct"))
    co2 = _num((latest or {}).get("air_quality_index"))
    co2_source = (latest or {}).get("co2_source")

    if temp is None:
        score -= 12
        reasons.append("missing temperature")
    elif temp < 20:
        score -= min(24, int((20 - temp) * 8))
        reasons.append("room is cool")
    elif temp > 24:
        score -= min(24, int((temp - 24) * 8))
        reasons.append("room is warm")

    if hum is None:
        score -= 12
        reasons.append("missing humidity")
    elif hum < 40:
        score -= min(30, int((40 - hum) * 3))
        reasons.append("air is dry")
    elif hum > 60:
        score -= min(24, int((hum - 60) * 2))
        reasons.append("air is humid")

    if co2_source == "sensor" and co2 is not None:
        if co2 >= 1200:
            score -= 30
            reasons.append("CO2 is high")
        elif co2 >= 800:
            score -= 14
            reasons.append("CO2 is rising")

    motion_events = 0
    if not history_df.empty and "motion_detected" in history_df.columns:
        motion_events = int((history_df["motion_detected"] == True).sum())

    score = max(0, min(100, score))
    if score >= 85:
        label = "Ready"
        tone = "#24c08b"
    elif score >= 70:
        label = "Comfortable"
        tone = "#25a7c8"
    elif score >= 50:
        label = "Watch"
        tone = "#d6a529"
    else:
        label = "Needs action"
        tone = "#e25555"
    return score, label, tone, reasons[:3], motion_events


def _weather_mood(weather):
    main = str((weather or {}).get("weather_main", "")).lower()
    temp = _num((weather or {}).get("temperature_c"))
    if "rain" in main or "drizzle" in main:
        return "Rain focus", "spotify: rain playlist", "#4ea5d9"
    if temp is not None and temp >= 24:
        return "Sunny energy", "spotify: hot playlist", "#d6a529"
    if temp is not None and temp <= 10:
        return "Cold start", "spotify: cold playlist", "#7aa7d9"
    if "clear" in main:
        return "Bright morning", "spotify: clear playlist", "#d6a529"
    if "cloud" in main:
        return "Calm cloudy", "spotify: cloud playlist", "#9aa6b2"
    return "Neutral day", "spotify: default playlist", "#25a7c8"


def _outfit_advice(weather):
    temp = _num((weather or {}).get("temperature_c"))
    main = str((weather or {}).get("weather_main", "")).lower()
    if "rain" in main or "drizzle" in main:
        return "Umbrella or rain jacket"
    if temp is not None and temp >= 24:
        return "Light clothes, sunglasses, sunscreen"
    if "clear" in main:
        return "Sunglasses, sunscreen if outside"
    if temp is not None and temp <= 10:
        return "Warm jacket or layers"
    if temp is not None and temp <= 16:
        return "Light jacket or layers"
    return "Comfortable clothes, light layer"


def _ventilation_advice(latest, weather):
    hum = _num((latest or {}).get("humidity_pct"))
    co2 = _num((latest or {}).get("air_quality_index"))
    co2_source = (latest or {}).get("co2_source")
    temp_in = _num((latest or {}).get("temperature_c"))
    temp_out = _num((weather or {}).get("temperature_c"))
    main = str((weather or {}).get("weather_main", "")).lower()

    if co2_source == "sensor" and co2 is not None and co2 >= 1200:
        return "Open window", "CO2 is high."
    if hum is not None and hum < 40:
        return "Avoid long airing", "Humidity is already low."
    if temp_in is not None and temp_out is not None and temp_in > 24 and temp_out < temp_in:
        return "Cool with outdoor air", "Outside is cooler."
    if "rain" in main or "drizzle" in main:
        return "Keep windows mostly closed", "Rain outside."
    return "Stable", "No urgent action."


def _morning_briefing(weather):
    if not weather:
        return "Good morning. Weather outside is unavailable. Wear: take a light layer just in case."
    condition = weather.get("weather_main") or "weather"
    return (
        "Good morning. Weather outside: "
        f"{_fmt(weather.get('temperature_c'), 1)} degrees, {condition}. "
        f"Wear: {_outfit_advice(weather)}."
    )


def _score_gauge(score, tone):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "/100", "font": {"color": "#f3f7f5", "size": 34}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#7f8b89"},
            "bar": {"color": tone},
            "bgcolor": "#141819",
            "borderwidth": 1,
            "bordercolor": "#2d3436",
            "steps": [
                {"range": [0, 50], "color": "#2b1d1f"},
                {"range": [50, 70], "color": "#2b281b"},
                {"range": [70, 85], "color": "#16282b"},
                {"range": [85, 100], "color": "#172821"},
            ],
        },
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=245,
        margin=dict(l=8, r=8, t=15, b=8),
    )
    return fig


def _motion_timeline(df):
    fig = go.Figure()
    if df.empty or "timestamp" not in df.columns or "motion_detected" not in df.columns:
        fig.add_annotation(text="No motion data yet", x=0.5, y=0.5, showarrow=False)
    else:
        motion_df = df[df["motion_detected"] == True].copy()
        if motion_df.empty:
            fig.add_annotation(text="No motion detected in this period", x=0.5, y=0.5, showarrow=False)
        else:
            motion_df["hour"] = motion_df["timestamp"].dt.floor("h")
            counts = motion_df.groupby("hour").size().reset_index(name="events")
            fig.add_trace(go.Bar(x=counts["hour"], y=counts["events"], marker_color="#d6a529"))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=245,
        margin=dict(l=5, r=5, t=28, b=5),
        yaxis_title="Motion",
        xaxis_title="",
    )
    return fig


def _mini_line(df, col, color, title):
    fig = go.Figure()
    if df.empty or col not in df.columns or "timestamp" not in df.columns:
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False)
    else:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df[col],
            mode="lines",
            fill="tozeroy",
            line=dict(color=color, width=2),
        ))
    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=210,
        margin=dict(l=5, r=5, t=38, b=5),
        showlegend=False,
    )
    return fig


def _card(label, value, detail="", accent="#25a7c8"):
    st.markdown(f"""
    <div class="dash-card">
        <div class="dash-label">{label}</div>
        <div class="dash-value" style="color:{accent};">{value}</div>
        <div class="dash-detail">{detail}</div>
    </div>
    """, unsafe_allow_html=True)


def render():
    with st.spinner("Updating your home view..."):
        latest = _latest_sensor()
        history_df = _to_df(_sensor_history(hours=24))
        weather = _current_weather()
        devices = _spotify_devices()

    score, comfort_label, tone, reasons, motion_count = _comfort_score(latest, history_df)
    action, _ = _ventilation_advice(latest, weather)
    mood, mood_detail, mood_color = _weather_mood(weather)
    briefing = _morning_briefing(weather)
    outfit = _outfit_advice(weather)
    active_devices = [device for device in devices if device.get("is_active")]
    spotify_state = active_devices[0].get("name") if active_devices else "Waiting for music app"

    st.markdown("""
    <div class="pixel-shell">
        <div class="hero-band">
            <div>
                <div class="eyebrow">PLAYER 1: HOME</div>
                <h1>Home Base</h1>
                <p>Motion wakes the assistant. Weather picks the advice. Spotify sets the mood.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    left, center, right = st.columns([0.95, 1.4, 0.95])
    with left:
        st.markdown('<div class="pixel-title">STATUS</div>', unsafe_allow_html=True)
        st.plotly_chart(_score_gauge(score, tone), use_container_width=True)
        _card("Room", comfort_label, ", ".join(reasons) if reasons else "Comfort OK", tone)

    with center:
        st.markdown('<div class="pixel-title">MORNING QUEST</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="routine-panel">
            <div class="dash-label">Assistant says</div>
            <div class="routine-text">{briefing}</div>
            <div class="routine-grid">
                <span>Motion</span>
                <span>Advice</span>
                <span>Voice</span>
                <span>Spotify</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div style="height: 6px;"></div>', unsafe_allow_html=True)
        controls = st.columns(2)
        with controls[0]:
            if st.button("Start mood track", use_container_width=True):
                try:
                    result = _post(
                        "/api/music/play-mood",
                        {"mood": (weather or {}).get("weather_main", "Clear"), "temperature_c": (weather or {}).get("temperature_c")},
                    )
                    st.success("Music started")
                except Exception as exc:
                    st.error("Music is unavailable right now.")
        with controls[1]:
            if st.button("Save weather", use_container_width=True):
                stored = _fetch("/api/weather/current", params={"store": "true"})
                st.success("Saved") if stored else st.warning("Not saved")

    with right:
        st.markdown('<div class="pixel-title">LOADOUT</div>', unsafe_allow_html=True)
        _card("Outdoor", f"{_fmt((weather or {}).get('temperature_c'), 1)} C", (weather or {}).get("weather_main", "Unavailable"), "#d6a529")
        _card("Wear", outfit, "", "#ffcc5c")
        _card("Music", mood, spotify_state, mood_color)

    st.markdown('<div class="pixel-title">SIGNALS</div>', unsafe_allow_html=True)
    chart_cols = st.columns([1, 1, 1])
    with chart_cols[0]:
        _card("Indoor", f"{_fmt((latest or {}).get('temperature_c'), 1)} C", f"{_fmt((latest or {}).get('humidity_pct'), 0)}% humidity", "#24c08b")
    with chart_cols[1]:
        _card("Motion", str(motion_count), "events / 24h", "#ffcc5c")
    with chart_cols[2]:
        _card("Air", action, "ventilation state", "#25a7c8")

    with st.expander("Show activity charts"):
        chart_cols = st.columns(3)
        with chart_cols[0]:
            st.plotly_chart(_mini_line(history_df, "temperature_c", "#25a7c8", "Indoor temperature"), use_container_width=True)
        with chart_cols[1]:
            st.plotly_chart(_mini_line(history_df, "humidity_pct", "#24c08b", "Humidity"), use_container_width=True)
        with chart_cols[2]:
            st.plotly_chart(_motion_timeline(history_df), use_container_width=True)

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
