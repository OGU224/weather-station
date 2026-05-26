"""
Data Archive page — Undertale RPG style history dashboard.
"""

import os
import sys
from datetime import datetime
from html import escape

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "https://weather-middleware-387666611940.europe-west1.run.app")
TIME_OPTIONS = {
    "Last 6 hours": 6,
    "Last 12 hours": 12,
    "Last 24 hours": 24,
    "Last 48 hours": 48,
    "Last 7 days": 168,
}

from pages.current import _companion, ALL_COMPANIONS

def _fetch(path, params=None):
    try:
        r = requests.get(f"{MIDDLEWARE_URL}{path}", params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    return None

def _rows_to_sensor(rows):
    return [{
        "timestamp": (r.get("timestamp").isoformat() if hasattr(r.get("timestamp"), "isoformat") else r.get("timestamp")),
        "device_id": r.get("device_id"),
        "temperature_c": r.get("temperature_c"),
        "humidity_pct": r.get("humidity_pct"),
        "air_quality_index": r.get("air_quality_index"),
        "air_quality_label": r.get("air_quality_label"),
        "co2_source": r.get("co2_source"),
        "motion_detected": r.get("motion_detected"),
    } for r in rows]

def _fetch_sensor_history(device_id, hours):
    params = {"hours": hours}
    if device_id:
        params["device_id"] = device_id
    data = _fetch("/api/sensors/history", params=params)
    if data:
        return data, "live"
    try:
        from data.bigquery_client import BigQueryClient
        rows = BigQueryClient().get_sensor_history(device_id=device_id, hours=hours)
        return _rows_to_sensor(rows), "stored"
    except Exception:
        return [], "unavailable"

def _rows_to_weather(rows):
    return [{
        "timestamp": (r.get("timestamp").isoformat() if hasattr(r.get("timestamp"), "isoformat") else r.get("timestamp")),
        "temperature_c": r.get("temperature_c"),
        "feels_like_c": r.get("feels_like_c"),
        "humidity_pct": r.get("humidity_pct"),
        "wind_speed_ms": r.get("wind_speed_ms"),
        "weather_main": r.get("weather_main"),
        "weather_description": r.get("weather_description"),
        "weather_icon": r.get("weather_icon"),
        "city": r.get("city"),
    } for r in rows]

def _fetch_weather_history(hours):
    data = _fetch("/api/weather/history", params={"hours": hours})
    if data:
        return data, "live"
    try:
        from data.bigquery_client import BigQueryClient
        rows = BigQueryClient().get_weather_history(hours=hours)
        return _rows_to_weather(rows), "stored"
    except Exception:
        return [], "unavailable"

def _store_weather_snapshot():
    try:
        r = requests.get(f"{MIDDLEWARE_URL}/api/weather/current", params={"store": "true"}, timeout=10)
        if r.status_code == 200:
            return True, "Weather snapshot saved."
    except requests.RequestException:
        pass
    try:
        from data.bigquery_client import BigQueryClient
        from services.weather_service import WeatherService
        weather = WeatherService().get_current_weather()
        if not weather:
            return False, "Could not read outdoor weather."
        if BigQueryClient().insert_weather_data(weather):
            return True, "Weather snapshot saved."
        return False, "Could not save snapshot."
    except Exception:
        return False, "Could not save snapshot."

def _to_df(data, time_col="timestamp"):
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df = df.rename(columns={"humidity_percent": "humidity_pct", "co2_ppm": "air_quality_index"})
    for col in ["temperature_c", "humidity_pct", "air_quality_index", "feels_like_c", "wind_speed_ms"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if time_col in df.columns:
        df[time_col] = pd.to_datetime(df[time_col], utc=True, errors="coerce")
        df = df.dropna(subset=[time_col]).sort_values(time_col)
    return df

def _fmt(v, d=1):
    if pd.isna(v):
        return "--"
    return f"{v:.{d}f}"

def _comfort_score(df):
    if df.empty:
        return 0, "No indoor data available.", []
    score = 100
    notes = []

    if "temperature_c" in df.columns and df["temperature_c"].notna().any():
        avg = df["temperature_c"].mean()
        if avg < 20:
            score -= min(25, int((20 - avg) * 6)); notes.append("cool room")
        elif avg > 24:
            score -= min(25, int((avg - 24) * 6)); notes.append("warm room")

    if "humidity_pct" in df.columns and df["humidity_pct"].notna().any():
        low = (df["humidity_pct"] < 40).mean()
        high = (df["humidity_pct"] > 60).mean()
        if low > 0:
            score -= min(35, int(low * 45)); notes.append("dry air")
        if high > 0:
            score -= min(25, int(high * 35)); notes.append("humid air")

    if "air_quality_index" in df.columns and df["air_quality_index"].notna().any():
        co2_df = df[df["co2_source"] == "sensor"] if "co2_source" in df.columns else df
        if not co2_df.empty and (co2_df["air_quality_index"] >= 1200).mean() > 0:
            score -= min(30, int((co2_df["air_quality_index"] >= 1200).mean() * 35))
            notes.append("high CO2")

    score = max(0, min(100, score))
    if score >= 80:
        label = "Comfortable conditions overall."
    elif score >= 60:
        label = "Mostly acceptable, some comfort issues."
    else:
        label = "Comfort issues were frequent."
    if notes:
        label += " Signal: " + ", ".join(notes[:2]) + "."
    return score, label, notes

def _ut_chart_layout(fig, title, height=260, y_title=""):
    fig.update_layout(
        title=dict(text=title, font=dict(family="Press Start 2P", size=9, color="#888")),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(showgrid=True, gridcolor="#1a1a1a", title=y_title),
    )
    return fig

def _ut_temp_chart(df, title="TEMPERATURE"):
    fig = go.Figure()
    if df.empty or "temperature_c" not in df.columns:
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
    else:
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["temperature_c"],
            mode="lines+markers", fill="tozeroy",
            line=dict(color="#25a7c8", width=2), marker=dict(size=3),
        ))
    return _ut_chart_layout(fig, title, y_title="C")

def _ut_hum_chart(df, title="HUMIDITY"):
    fig = go.Figure()
    if df.empty or "humidity_pct" not in df.columns:
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
    else:
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["humidity_pct"],
            mode="lines+markers", fill="tozeroy",
            line=dict(color="#24c08b", width=2), marker=dict(size=3),
        ))
        fig.add_hline(y=40, line_dash="dash", line_color="#e25555",
                      annotation_text="Alert 40%", annotation_font_color="#e25555")
    return _ut_chart_layout(fig, title, y_title="%")

def _ut_co2_chart(df, title="CO2"):
    fig = go.Figure()
    co2_df = df
    if "co2_source" in df.columns:
        co2_df = df[df["co2_source"] == "sensor"]
    if co2_df.empty or "air_quality_index" not in co2_df.columns or co2_df["air_quality_index"].isna().all():
        fig.add_annotation(text="No CO2 sensor data", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
    else:
        colors = co2_df["air_quality_index"].apply(
            lambda v: "#24c08b" if v < 800 else ("#d6a529" if v < 1200 else "#e25555")
        ).tolist()
        fig.add_trace(go.Bar(x=co2_df["timestamp"], y=co2_df["air_quality_index"], marker_color=colors))
    return _ut_chart_layout(fig, title, y_title="ppm")

def _ut_motion_chart(df, title="MOTION EVENTS"):
    fig = go.Figure()
    if df.empty or "motion_detected" not in df.columns:
        fig.add_annotation(text="No motion data", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
    else:
        mdf = df[df["motion_detected"] == True].copy()
        if mdf.empty:
            fig.add_annotation(text="No motion detected", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
        else:
            mdf["hour"] = mdf["timestamp"].dt.floor("h")
            counts = mdf.groupby("hour").size().reset_index(name="events")
            fig.add_trace(go.Bar(x=counts["hour"], y=counts["events"], marker_color="#d6a529"))
    return _ut_chart_layout(fig, title, y_title="events")

def _ut_section(title):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:22px 0 12px 0;">
        <div style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.52rem;letter-spacing:0.1em;">{escape(title)}</div>
        <div style="flex:1;height:2px;background:#2e3b47;"></div>
    </div>
    """, unsafe_allow_html=True)

def _ut_stat(label, value, color="#25a7c8"):
    st.markdown(f"""
    <div style="background:#0a0a0a;border:3px solid #2e3b47;padding:14px 16px;margin-bottom:8px;text-align:center;">
        <div style="color:#666;font-family:'Press Start 2P',monospace;font-size:0.4rem;margin-bottom:6px;">{escape(label)}</div>
        <div style="color:{color};font-size:1.5rem;font-weight:700;">{escape(str(value))}</div>
    </div>
    """, unsafe_allow_html=True)

def _ut_hp(label, value, max_val=100, color="#24c08b"):
    pct = max(0, min(100, int(value / max_val * 100))) if max_val > 0 else 0
    st.markdown(f"""
    <div style="margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.42rem;">{escape(label)}</span>
            <span style="color:#aaa;font-size:0.75rem;">{value}/100</span>
        </div>
        <div style="height:14px;background:#440000;border:2px solid {color};">
            <div style="height:100%;width:{pct}%;background:{color};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def _ut_dialogue(speaker, text, companion_idx=0):
    st.markdown(f"""
    <div style="display:flex;align-items:flex-start;gap:16px;background:#000;border:3px solid #fff;padding:16px 18px;margin-bottom:14px;">
        <div style="flex-shrink:0;margin-top:4px;">{_companion(companion_idx, 48)}</div>
        <div style="flex:1;">
            <div style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.48rem;margin-bottom:8px;">{escape(speaker)}</div>
            <div style="color:#fff;font-size:0.88rem;line-height:1.5;">* {escape(text)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def _companion_divider():
    html = '<div style="display:flex;justify-content:center;gap:20px;padding:6px 0;margin:10px 0;opacity:0.35;">'
    for i in range(3):
        html += _companion(i, 24)
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def render():
    st.markdown(f"""
    <div style="background:#000;border:3px solid #fff;padding:18px 22px;margin-bottom:16px;position:relative;">
        <div style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.5rem;margin-bottom:8px;">DATA ARCHIVE</div>
        <div style="color:#fff;font-size:1.6rem;font-weight:700;">History Vault</div>
        <div style="color:#888;font-size:0.88rem;margin-top:4px;">Replay sensor runs and compare indoor comfort with outdoor weather.</div>
    </div>
    """, unsafe_allow_html=True)

    # Zone de contrôle unifiée (Filtre par pièce nettoyé)
    selected_range = st.selectbox("Replay window", list(TIME_OPTIONS.keys()), index=2)
    device_id = "" # Fixé par défaut pour tout l'historique

    hours = TIME_OPTIONS[selected_range]

    with st.spinner("* Loading history vault..."):
        sensor_data, _ = _fetch_sensor_history(device_id=device_id, hours=hours)
        weather_data, _ = _fetch_weather_history(hours=hours)

    sensor_df = _to_df(sensor_data or [])
    weather_df = _to_df(weather_data or [])

    if sensor_df.empty and weather_df.empty:
        _ut_dialogue("Robot", "No history found yet. Let the station collect a few readings first.", 1)
        return

    _ut_section("INDOOR RECAP")

    if not sensor_df.empty:
        score, recommendation, notes = _comfort_score(sensor_df)

        temp_avg = sensor_df["temperature_c"].mean() if "temperature_c" in sensor_df.columns else float("nan")
        hum_avg = sensor_df["humidity_pct"].mean() if "humidity_pct" in sensor_df.columns else float("nan")
        low_hum_count = int((sensor_df["humidity_pct"] < 40).sum()) if "humidity_pct" in sensor_df.columns else 0
        motion_count = int((sensor_df["motion_detected"] == True).sum()) if "motion_detected" in sensor_df.columns else 0

        score_color = "#24c08b" if score >= 80 else ("#d6a529" if score >= 60 else "#e25555")
        _ut_hp("COMFORT", score, 100, score_color)

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            _ut_stat("Avg Temp", f"{_fmt(temp_avg)}C", "#25a7c8")
        with s2:
            _ut_stat("Avg Hum", f"{_fmt(hum_avg)}%", "#24c08b")
        with s3:
            _ut_stat("Motion", str(motion_count), "#d6a529")
        with s4:
            _ut_stat("Readings", str(len(sensor_df)), "#888")

        if low_hum_count:
            _ut_dialogue("Robot", f"Humidity was below 40% for {low_hum_count} reading(s) in this period.", 1)

        if "humidity_pct" in sensor_df.columns and sensor_df["humidity_pct"].notna().any():
            lowest = sensor_df.loc[sensor_df["humidity_pct"].idxmin()]
            lowest_time = lowest["timestamp"].strftime("%Y-%m-%d %H:%M")
            st.caption(f"Lowest humidity: {_fmt(lowest['humidity_pct'])}% at {lowest_time}.")

        st.markdown(f"""
        <div style="background:#0a0a0a;border:3px solid #2e3b47;border-left:4px solid {score_color};padding:12px 16px;margin:8px 0 16px 0;">
            <div style="color:#aaa;font-size:0.82rem;line-height:1.45;">* {escape(recommendation)}</div>
        </div>
        """, unsafe_allow_html=True)

        _companion_divider()

        _ut_section("INDOOR TRACES")

        tab_temp, tab_hum, tab_co2 = st.tabs(["Temp", "Humidity", "CO2"])
        with tab_temp:
            st.plotly_chart(_ut_temp_chart(sensor_df, "INDOOR TEMPERATURE"), use_container_width=True)
        with tab_hum:
            st.plotly_chart(_ut_hum_chart(sensor_df, "INDOOR HUMIDITY"), use_container_width=True)
        with tab_co2:
            st.plotly_chart(_ut_co2_chart(sensor_df, "CO2 FROM SENSOR"), use_container_width=True)

        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        st.plotly_chart(_ut_motion_chart(sensor_df, "MOTION BY HOUR"), use_container_width=True)
    else:
        _ut_dialogue("Ghost", "No indoor sensor data available for this period.", 0)

    _companion_divider()
    _ut_section("OUTDOOR TIMELINE")

    with st.expander("Weather capture"):
        if st.button("Save outdoor now", use_container_width=True):
            ok, msg = _store_weather_snapshot()
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    if not weather_df.empty:
        tab_out_t, tab_out_h = st.tabs(["Temp", "Humidity"])
        with tab_out_t:
            st.plotly_chart(_ut_temp_chart(weather_df, "OUTDOOR TEMPERATURE"), use_container_width=True)
        with tab_out_h:
            st.plotly_chart(_ut_hum_chart(weather_df, "OUTDOOR HUMIDITY"), use_container_width=True)
    else:
        _ut_dialogue("Cat", "No outdoor weather history yet.", 2)

    _companion_divider()
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")