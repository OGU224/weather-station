"""
Smart Home page — Undertale RPG aesthetic with pixel companions.
"""

import os
import sys
from datetime import datetime, timezone
from html import escape

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, REPO_ROOT)

MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "https://weather-middleware-387666611940.europe-west1.run.app")

# ── Companion SVG sprites (16x16 pixel art, rendered as inline SVG) ──────────

GHOST_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="6" y="1" width="4" height="1" fill="#fff"/>
<rect x="4" y="2" width="8" height="1" fill="#fff"/>
<rect x="3" y="3" width="10" height="1" fill="#fff"/>
<rect x="2" y="4" width="12" height="2" fill="#fff"/>
<rect x="2" y="6" width="2" height="1" fill="#fff"/><rect x="4" y="6" width="1" height="1" fill="#111"/><rect x="5" y="6" width="5" height="1" fill="#fff"/><rect x="10" y="6" width="1" height="1" fill="#111"/><rect x="11" y="6" width="3" height="1" fill="#fff"/>
<rect x="2" y="7" width="2" height="1" fill="#fff"/><rect x="4" y="7" width="2" height="1" fill="#111"/><rect x="6" y="7" width="4" height="1" fill="#fff"/><rect x="10" y="7" width="2" height="1" fill="#111"/><rect x="12" y="7" width="2" height="1" fill="#fff"/>
<rect x="2" y="8" width="12" height="1" fill="#fff"/>
<rect x="2" y="9" width="5" height="1" fill="#fff"/><rect x="7" y="9" width="2" height="1" fill="#111"/><rect x="9" y="9" width="5" height="1" fill="#fff"/>
<rect x="2" y="10" width="12" height="2" fill="#fff"/>
<rect x="2" y="12" width="3" height="1" fill="#fff"/><rect x="6" y="12" width="4" height="1" fill="#fff"/><rect x="11" y="12" width="3" height="1" fill="#fff"/>
<rect x="2" y="13" width="2" height="1" fill="#fff"/><rect x="6" y="13" width="2" height="1" fill="#fff"/><rect x="11" y="13" width="2" height="1" fill="#fff"/>
</svg>"""

SKULL_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="5" y="1" width="6" height="1" fill="#fff"/>
<rect x="3" y="2" width="10" height="1" fill="#fff"/>
<rect x="2" y="3" width="12" height="1" fill="#fff"/>
<rect x="2" y="4" width="2" height="1" fill="#fff"/><rect x="4" y="4" width="4" height="1" fill="#111"/><rect x="8" y="4" width="1" height="1" fill="#fff"/><rect x="9" y="4" width="4" height="1" fill="#111"/><rect x="13" y="4" width="1" height="1" fill="#fff"/>
<rect x="2" y="5" width="2" height="1" fill="#fff"/><rect x="4" y="5" width="1" height="1" fill="#111"/><rect x="5" y="5" width="2" height="1" fill="#0df"/><rect x="7" y="5" width="2" height="1" fill="#111"/><rect x="9" y="5" width="1" height="1" fill="#111"/><rect x="10" y="5" width="2" height="1" fill="#0df"/><rect x="12" y="5" width="2" height="1" fill="#fff"/>
<rect x="2" y="6" width="2" height="1" fill="#fff"/><rect x="4" y="6" width="4" height="1" fill="#111"/><rect x="8" y="6" width="1" height="1" fill="#fff"/><rect x="9" y="6" width="4" height="1" fill="#111"/><rect x="13" y="6" width="1" height="1" fill="#fff"/>
<rect x="2" y="7" width="12" height="1" fill="#fff"/>
<rect x="2" y="8" width="5" height="1" fill="#fff"/><rect x="7" y="8" width="2" height="1" fill="#111"/><rect x="9" y="8" width="5" height="1" fill="#fff"/>
<rect x="2" y="9" width="1" height="1" fill="#fff"/><rect x="3" y="9" width="1" height="1" fill="#111"/><rect x="4" y="9" width="1" height="1" fill="#fff"/><rect x="5" y="9" width="1" height="1" fill="#111"/><rect x="6" y="9" width="1" height="1" fill="#fff"/><rect x="7" y="9" width="1" height="1" fill="#111"/><rect x="8" y="9" width="1" height="1" fill="#fff"/><rect x="9" y="9" width="1" height="1" fill="#111"/><rect x="10" y="9" width="1" height="1" fill="#fff"/><rect x="11" y="9" width="1" height="1" fill="#111"/><rect x="12" y="9" width="2" height="1" fill="#fff"/>
<rect x="3" y="10" width="10" height="1" fill="#fff"/>
<rect x="4" y="11" width="8" height="1" fill="#6bf"/>
<rect x="3" y="12" width="10" height="2" fill="#6bf"/>
<rect x="4" y="14" width="2" height="1" fill="#6bf"/><rect x="9" y="14" width="2" height="1" fill="#6bf"/>
</svg>"""

FLOWER_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="6" y="0" width="4" height="1" fill="#ff0"/>
<rect x="3" y="1" width="3" height="1" fill="#ff0"/><rect x="6" y="1" width="4" height="1" fill="#ff0"/><rect x="10" y="1" width="3" height="1" fill="#ff0"/>
<rect x="2" y="2" width="3" height="1" fill="#ff0"/><rect x="5" y="2" width="6" height="1" fill="#fec"/><rect x="11" y="2" width="3" height="1" fill="#ff0"/>
<rect x="2" y="3" width="1" height="1" fill="#ff0"/><rect x="3" y="3" width="10" height="1" fill="#fec"/><rect x="13" y="3" width="1" height="1" fill="#ff0"/>
<rect x="2" y="4" width="1" height="1" fill="#ff0"/><rect x="3" y="4" width="2" height="1" fill="#fec"/><rect x="5" y="4" width="2" height="1" fill="#111"/><rect x="7" y="4" width="2" height="1" fill="#fec"/><rect x="9" y="4" width="2" height="1" fill="#111"/><rect x="11" y="4" width="2" height="1" fill="#fec"/><rect x="13" y="4" width="1" height="1" fill="#ff0"/>
<rect x="2" y="5" width="1" height="1" fill="#ff0"/><rect x="3" y="5" width="10" height="1" fill="#fec"/><rect x="13" y="5" width="1" height="1" fill="#ff0"/>
<rect x="2" y="6" width="1" height="1" fill="#ff0"/><rect x="3" y="6" width="3" height="1" fill="#fec"/><rect x="6" y="6" width="4" height="1" fill="#111"/><rect x="10" y="6" width="3" height="1" fill="#fec"/><rect x="13" y="6" width="1" height="1" fill="#ff0"/>
<rect x="3" y="7" width="3" height="1" fill="#ff0"/><rect x="6" y="7" width="4" height="1" fill="#ff0"/><rect x="10" y="7" width="3" height="1" fill="#ff0"/>
<rect x="7" y="8" width="2" height="4" fill="#0a0"/>
<rect x="5" y="9" width="2" height="1" fill="#0a0"/><rect x="9" y="10" width="2" height="1" fill="#0a0"/>
<rect x="4" y="12" width="8" height="2" fill="#a52"/>
</svg>"""

CAT_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="2" y="0" width="2" height="1" fill="#fff"/><rect x="12" y="0" width="2" height="1" fill="#fff"/>
<rect x="2" y="1" width="3" height="1" fill="#fff"/><rect x="11" y="1" width="3" height="1" fill="#fff"/>
<rect x="2" y="2" width="1" height="1" fill="#f8a"/><rect x="3" y="2" width="2" height="1" fill="#fff"/><rect x="11" y="2" width="2" height="1" fill="#fff"/><rect x="13" y="2" width="1" height="1" fill="#f8a"/>
<rect x="3" y="3" width="10" height="2" fill="#fff"/>
<rect x="3" y="5" width="1" height="1" fill="#fff"/><rect x="4" y="5" width="2" height="1" fill="#111"/><rect x="6" y="5" width="4" height="1" fill="#fff"/><rect x="10" y="5" width="2" height="1" fill="#111"/><rect x="12" y="5" width="1" height="1" fill="#fff"/>
<rect x="3" y="6" width="1" height="1" fill="#fff"/><rect x="4" y="6" width="1" height="1" fill="#0c0"/><rect x="5" y="6" width="1" height="1" fill="#111"/><rect x="6" y="6" width="4" height="1" fill="#fff"/><rect x="10" y="6" width="1" height="1" fill="#0c0"/><rect x="11" y="6" width="1" height="1" fill="#111"/><rect x="12" y="6" width="1" height="1" fill="#fff"/>
<rect x="1" y="7" width="2" height="1" fill="#999"/><rect x="3" y="7" width="4" height="1" fill="#fff"/><rect x="7" y="7" width="2" height="1" fill="#f8a"/><rect x="9" y="7" width="4" height="1" fill="#fff"/><rect x="13" y="7" width="2" height="1" fill="#999"/>
<rect x="3" y="8" width="10" height="4" fill="#fff"/>
<rect x="3" y="12" width="2" height="2" fill="#fff"/><rect x="9" y="12" width="2" height="2" fill="#fff"/>
<rect x="12" y="10" width="1" height="1" fill="#fff"/><rect x="13" y="9" width="1" height="1" fill="#fff"/><rect x="14" y="8" width="1" height="2" fill="#fff"/>
</svg>"""

ROBOT_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="7" y="0" width="2" height="1" fill="#ff0"/>
<rect x="7" y="1" width="2" height="1" fill="#999"/>
<rect x="3" y="2" width="10" height="1" fill="#999"/>
<rect x="3" y="3" width="10" height="6" fill="#222"/>
<rect x="3" y="3" width="1" height="6" fill="#999"/><rect x="12" y="3" width="1" height="6" fill="#999"/>
<rect x="5" y="5" width="2" height="2" fill="#0c0"/><rect x="9" y="5" width="2" height="2" fill="#0c0"/>
<rect x="5" y="8" width="6" height="1" fill="#0c0"/>
<rect x="3" y="9" width="10" height="1" fill="#999"/>
<rect x="2" y="10" width="2" height="1" fill="#999"/><rect x="4" y="10" width="8" height="3" fill="#999"/><rect x="12" y="10" width="2" height="1" fill="#999"/>
<rect x="5" y="11" width="2" height="1" fill="#555"/><rect x="7" y="11" width="2" height="1" fill="#f22"/><rect x="9" y="11" width="2" height="1" fill="#555"/>
<rect x="4" y="13" width="2" height="2" fill="#999"/><rect x="9" y="13" width="2" height="2" fill="#999"/>
</svg>"""

MUSHROOM_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="6" y="0" width="6" height="1" fill="#f22"/>
<rect x="4" y="1" width="10" height="1" fill="#f22"/>
<rect x="2" y="2" width="2" height="1" fill="#f22"/><rect x="4" y="2" width="2" height="1" fill="#fff"/><rect x="6" y="2" width="5" height="1" fill="#f22"/><rect x="11" y="2" width="2" height="1" fill="#fff"/><rect x="13" y="2" width="2" height="1" fill="#f22"/>
<rect x="2" y="3" width="14" height="1" fill="#f22"/>
<rect x="1" y="4" width="5" height="1" fill="#f22"/><rect x="6" y="4" width="2" height="1" fill="#fff"/><rect x="8" y="4" width="7" height="1" fill="#f22"/>
<rect x="1" y="5" width="14" height="1" fill="#f22"/>
<rect x="2" y="6" width="12" height="2" fill="#fec"/>
<rect x="3" y="8" width="2" height="2" fill="#111"/><rect x="5" y="8" width="3" height="2" fill="#fec"/><rect x="8" y="8" width="2" height="2" fill="#111"/><rect x="10" y="8" width="3" height="2" fill="#fec"/>
<rect x="2" y="9" width="1" height="1" fill="#f8a"/><rect x="12" y="9" width="1" height="1" fill="#f8a"/>
<rect x="3" y="10" width="3" height="1" fill="#fec"/><rect x="6" y="10" width="2" height="1" fill="#111"/><rect x="8" y="10" width="5" height="1" fill="#fec"/>
<rect x="4" y="11" width="8" height="1" fill="#fec"/>
<rect x="5" y="12" width="6" height="1" fill="#fec"/>
<rect x="4" y="13" width="8" height="2" fill="#a52"/>
</svg>"""

ALL_COMPANIONS = [
    ("Ghost", GHOST_SVG), ("Skull", SKULL_SVG), ("Flower", FLOWER_SVG),
    ("Cat", CAT_SVG), ("Robot", ROBOT_SVG), ("Mushroom", MUSHROOM_SVG),
]


def _companion(index, size=48):
    _, svg = ALL_COMPANIONS[index % len(ALL_COMPANIONS)]
    return svg.format(s=size)


# ── Data fetching (same logic as before) ──────────────────────────────────────

def _fetch(path, params=None):
    try:
        r = requests.get(f"{MIDDLEWARE_URL}{path}", params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    return None


def _post(path, payload=None, timeout=18):
    r = requests.post(f"{MIDDLEWARE_URL}{path}", json=payload or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


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


def _sensor_history(hours=24):
    data = _fetch("/api/sensors/history", params={"hours": hours})
    if data:
        return data
    try:
        from data.bigquery_client import BigQueryClient
        rows = BigQueryClient().get_sensor_history(hours=hours)
        return [{
            "timestamp": (r.get("timestamp").isoformat() if hasattr(r.get("timestamp"), "isoformat") else r.get("timestamp")),
            "temperature_c": r.get("temperature_c"),
            "humidity_pct": r.get("humidity_pct"),
            "air_quality_index": r.get("air_quality_index"),
            "co2_source": r.get("co2_source"),
            "motion_detected": r.get("motion_detected"),
        } for r in rows]
    except Exception:
        return []


def _current_weather():
    data = _fetch("/api/weather/current")
    if data:
        return data
    try:
        from services.weather_service import WeatherService
        w = WeatherService().get_current_weather()
        return w.to_dict() if w else None
    except Exception:
        return None


def _forecast(days=3):
    data = _fetch("/api/weather/forecast", params={"days": days})
    if data:
        return data
    try:
        from dataclasses import asdict
        from services.weather_service import WeatherService
        return [asdict(d) for d in WeatherService().get_forecast(days=days)]
    except Exception:
        return []


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


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _fmt(v, d=1, s=""):
    v = _num(v)
    return f"{v:.{d}f}{s}" if v is not None else "--"


def _age_label(ts):
    if not ts:
        return "--"
    try:
        t = pd.to_datetime(ts, utc=True)
    except Exception:
        return "--"
    if pd.isna(t):
        return "--"
    mins = max(0, (datetime.now(timezone.utc) - t.to_pydatetime()).total_seconds() / 60)
    if mins < 1:
        return "now"
    if mins < 60:
        return f"{int(mins)}m ago"
    return f"{round(mins / 60, 1)}h ago"


# ── Game logic ────────────────────────────────────────────────────────────────

def _comfort_score(latest, df):
    score = 100
    reasons = []
    temp = _num((latest or {}).get("temperature_c"))
    hum = _num((latest or {}).get("humidity_pct"))
    co2 = _num((latest or {}).get("air_quality_index"))
    co2_src = (latest or {}).get("co2_source")

    if temp is None:
        score -= 12; reasons.append("no temp data")
    elif temp < 20:
        score -= min(24, int((20 - temp) * 8)); reasons.append("room is cool")
    elif temp > 24:
        score -= min(24, int((temp - 24) * 8)); reasons.append("room is warm")

    if hum is None:
        score -= 12; reasons.append("no humidity data")
    elif hum < 40:
        score -= min(30, int((40 - hum) * 3)); reasons.append("air is dry")
    elif hum > 60:
        score -= min(24, int((hum - 60) * 2)); reasons.append("air is humid")

    if co2_src == "sensor" and co2 is not None:
        if co2 >= 1200:
            score -= 30; reasons.append("CO2 high")
        elif co2 >= 800:
            score -= 14; reasons.append("CO2 rising")

    motion = 0
    if not df.empty and "motion_detected" in df.columns:
        motion = int((df["motion_detected"] == True).sum())

    score = max(0, min(100, score))
    if score >= 85:
        rank, color = "S", "#24c08b"
    elif score >= 70:
        rank, color = "A", "#25a7c8"
    elif score >= 50:
        rank, color = "B", "#d6a529"
    else:
        rank, color = "D", "#e25555"
    return score, rank, color, reasons[:3], motion


def _outfit(weather):
    temp = _num((weather or {}).get("temperature_c"))
    main = str((weather or {}).get("weather_main", "")).lower()
    if "rain" in main or "drizzle" in main:
        return "Umbrella or rain jacket"
    if temp is not None and temp >= 24:
        return "Light clothes, sunglasses"
    if "clear" in main:
        return "Sunglasses, sunscreen"
    if temp is not None and temp <= 10:
        return "Warm jacket, layers"
    if temp is not None and temp <= 16:
        return "Light jacket"
    return "Comfortable clothes"


def _ventilation(latest, weather):
    hum = _num((latest or {}).get("humidity_pct"))
    co2 = _num((latest or {}).get("air_quality_index"))
    co2_src = (latest or {}).get("co2_source")
    main = str((weather or {}).get("weather_main", "")).lower()
    if co2_src == "sensor" and co2 is not None and co2 >= 1200:
        return "Open window", "#e25555"
    if hum is not None and hum < 40:
        return "Keep closed", "#d6a529"
    if "rain" in main:
        return "Keep closed", "#4ea5d9"
    return "Stable", "#24c08b"


def _objectives(score, latest, weather):
    objs = []
    hum = _num((latest or {}).get("humidity_pct"))
    temp = _num((latest or {}).get("temperature_c"))
    co2 = _num((latest or {}).get("air_quality_index"))
    co2_src = (latest or {}).get("co2_source")
    main = str((weather or {}).get("weather_main", "")).lower()

    objs.append(("Room comfort", score >= 85))
    if hum is not None:
        objs.append(("Humidity 40-60%", 40 <= hum <= 60))
    else:
        objs.append(("Humidity scan", False))
    if temp is not None:
        objs.append(("Temp 20-24C", 20 <= temp <= 24))
    else:
        objs.append(("Temp scan", False))
    if co2_src == "sensor" and co2 is not None:
        objs.append(("Air quality", co2 < 800))
    if "rain" in main:
        objs.append(("Umbrella ready", False))
    elif weather:
        objs.append(("Outdoor checked", True))
    return objs[:5]


# ── Charts ────────────────────────────────────────────────────────────────────

def _gauge(score, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "", "font": {"color": "#f3f7f5", "size": 38, "family": "Press Start 2P"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#444", "tickfont": {"size": 9}},
            "bar": {"color": color},
            "bgcolor": "#141819",
            "borderwidth": 2, "bordercolor": "#2e3b47",
            "steps": [
                {"range": [0, 50], "color": "#1a1010"},
                {"range": [50, 70], "color": "#1a1a10"},
                {"range": [70, 85], "color": "#101a1a"},
                {"range": [85, 100], "color": "#101a10"},
            ],
        },
    ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=200, margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


def _spark(df, col, color, title):
    fig = go.Figure()
    if df.empty or col not in df.columns:
        fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
    else:
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df[col], mode="lines", fill="tozeroy",
            line=dict(color=color, width=2),
        ))
    fig.update_layout(
        title=dict(text=title, font=dict(family="Press Start 2P", size=8, color="#888")),
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=170, margin=dict(l=5, r=5, t=30, b=5), showlegend=False,
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
    )
    return fig


# ── UI Components ─────────────────────────────────────────────────────────────

def _ut_box(label, value, detail="", color="#25a7c8", companion_idx=None):
    """Undertale-style stat card with optional companion sprite."""
    sprite = ""
    if companion_idx is not None:
        sprite = f'<div style="position:absolute;top:8px;right:8px;opacity:0.3;">{_companion(companion_idx, 32)}</div>'
    st.markdown(f"""
    <div style="background:#111;border:3px solid #2e3b47;padding:14px 16px;position:relative;margin-bottom:8px;min-height:90px;">
        {sprite}
        <div style="color:#666;font-family:'Press Start 2P',monospace;font-size:0.45rem;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">{escape(label)}</div>
        <div style="color:{color};font-size:1.4rem;font-weight:700;line-height:1.1;">{escape(str(value))}</div>
        <div style="color:#888;font-size:0.8rem;margin-top:4px;">{escape(detail)}</div>
    </div>
    """, unsafe_allow_html=True)


def _ut_dialogue(speaker, text, companion_idx=0):
    """Undertale dialogue box with companion sprite."""
    st.markdown(f"""
    <div style="display:flex;align-items:flex-start;gap:14px;background:#000;border:3px solid #fff;padding:14px 16px;margin-bottom:12px;">
        <div style="flex-shrink:0;margin-top:2px;">{_companion(companion_idx, 52)}</div>
        <div style="flex:1;">
            <div style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.5rem;margin-bottom:6px;">{escape(speaker)}</div>
            <div style="color:#fff;font-size:0.88rem;line-height:1.5;">* {escape(text)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _ut_objectives(objs):
    """Render quest objectives as Undertale menu items."""
    html = '<div style="background:#111;border:3px solid #2e3b47;padding:12px 14px;margin-bottom:8px;">'
    html += '<div style="color:#666;font-family:\'Press Start 2P\',monospace;font-size:0.45rem;margin-bottom:8px;">QUEST LOG</div>'
    for text, done in objs:
        color = "#24c08b" if done else "#d6a529"
        heart = "&#9829;" if done else "&#9825;"
        html += f'<div style="color:{color};font-size:0.78rem;padding:3px 0;font-family:monospace;">{heart} {escape(text)}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def _ut_hp_bar(label, value, max_val=100, color="#24c08b"):
    """HP-style bar."""
    pct = max(0, min(100, int(value / max_val * 100))) if max_val > 0 else 0
    st.markdown(f"""
    <div style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
            <span style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.45rem;">{escape(label)}</span>
            <span style="color:#fff;font-size:0.75rem;">{value} / {max_val}</span>
        </div>
        <div style="height:12px;background:#440000;border:2px solid {color};">
            <div style="height:100%;width:{pct}%;background:{color};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _ut_forecast_row(forecasts):
    """Compact forecast strip."""
    if not forecasts:
        st.caption("No forecast data yet.")
        return
    html = '<div style="display:flex;gap:6px;margin-bottom:8px;">'
    for fc in forecasts[:5]:
        date = str(fc.get("date", ""))[-5:]
        t_max = round(_num(fc.get("temp_max"), 0), 1)
        t_min = round(_num(fc.get("temp_min"), 0), 1)
        main = str(fc.get("weather_main", ""))[:6]
        icon = fc.get("weather_icon", "")
        icon_url = f"https://openweathermap.org/img/wn/{icon}@2x.png" if icon else ""
        html += f"""
        <div style="flex:1;background:#111;border:2px solid #2e3b47;padding:8px 6px;text-align:center;">
            <div style="color:#888;font-size:0.6rem;">{date}</div>
            {"<img src='" + icon_url + "' width='28' style='margin:2px auto;display:block;'/>" if icon_url else f"<div style='color:#fff;font-size:0.7rem;margin:4px 0;'>{main}</div>"}
            <div style="color:#0df;font-size:0.75rem;font-weight:700;">{t_max}C</div>
            <div style="color:#666;font-size:0.6rem;">{t_min}C</div>
        </div>"""
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ── Companion decoration strip ────────────────────────────────────────────────

def _companion_strip():
    """Row of all 6 companions as decoration."""
    html = '<div style="display:flex;justify-content:center;gap:16px;padding:8px 0;margin-bottom:12px;opacity:0.6;">'
    for i in range(6):
        html += _companion(i, 36)
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    with st.spinner("* Loading your world..."):
        latest = _latest_sensor()
        history_df = _to_df(_sensor_history(hours=24))
        weather = _current_weather()
        fcast = _forecast(days=5)

    score, rank, color, reasons, motion_count = _comfort_score(latest, history_df)
    outfit_text = _outfit(weather)
    vent_text, vent_color = _ventilation(latest, weather)
    objs = _objectives(score, latest, weather)

    # ── Hero banner with companions ──
    st.markdown(f"""
    <div style="background:#000;border:3px solid #fff;padding:16px 20px;margin-bottom:14px;position:relative;overflow:hidden;">
        <div style="position:absolute;top:10px;right:16px;opacity:0.15;display:flex;gap:8px;">
            {_companion(0, 42)}{_companion(1, 42)}{_companion(3, 42)}
        </div>
        <div style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.5rem;margin-bottom:6px;">PLAYER 1 : HOME</div>
        <div style="color:#fff;font-size:1.5rem;font-weight:700;">Home Base</div>
        <div style="color:#888;font-size:0.85rem;margin-top:4px;">Room comfort RPG. Keep your stats high.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Morning briefing dialogue ──
    w_main = str((weather or {}).get("weather_main", "weather")).lower()
    w_temp = _fmt((weather or {}).get("temperature_c"), 1)
    briefing = f"Good morning. Outside: {w_temp}C, {w_main}. Wear: {outfit_text.lower()}."
    if not weather:
        briefing = "Good morning. Weather data unavailable. Take a light layer just in case."

    buddy_idx = 0
    if "rain" in w_main:
        buddy_idx = 0  # Ghost cries in rain
    elif _num((weather or {}).get("temperature_c"), 20) >= 24:
        buddy_idx = 2  # Flower loves sun
    elif score < 50:
        buddy_idx = 4  # Robot for alerts
    else:
        buddy_idx = 3  # Cat for chill

    _ut_dialogue("Morning Assistant", briefing, buddy_idx)

    # ── Top row: HP + Rank + Weather ──
    col1, col2, col3 = st.columns([1.2, 0.8, 1])

    with col1:
        st.markdown(f'<div style="color:#666;font-family:\'Press Start 2P\',monospace;font-size:0.45rem;margin-bottom:6px;">ROOM HP</div>', unsafe_allow_html=True)
        _ut_hp_bar("HP", score, 100, color)
        _ut_hp_bar("HUM", int(_num((latest or {}).get("humidity_pct"), 0)), 100,
                    "#e25555" if _num((latest or {}).get("humidity_pct"), 50) < 40 else "#24c08b")
        if reasons:
            st.caption("* " + ", ".join(reasons))

    with col2:
        st.markdown(f"""
        <div style="background:#111;border:3px solid #2e3b47;padding:16px;text-align:center;min-height:130px;">
            <div style="color:#666;font-family:'Press Start 2P',monospace;font-size:0.45rem;margin-bottom:8px;">RANK</div>
            <div style="color:{color};font-family:'Press Start 2P',monospace;font-size:2.5rem;line-height:1;">{rank}</div>
            <div style="color:#888;font-size:0.75rem;margin-top:6px;">Score {score}/100</div>
            <div style="margin-top:8px;">{_companion(buddy_idx, 40)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        w_icon = (weather or {}).get("weather_icon", "")
        icon_url = f"https://openweathermap.org/img/wn/{w_icon}@2x.png" if w_icon else ""
        st.markdown(f"""
        <div style="background:#111;border:3px solid #2e3b47;padding:14px;text-align:center;min-height:130px;">
            <div style="color:#666;font-family:'Press Start 2P',monospace;font-size:0.45rem;margin-bottom:4px;">OUTDOOR</div>
            {"<img src='" + icon_url + "' width='44' style='margin:0 auto;display:block;'/>" if icon_url else ""}
            <div style="color:#fb923c;font-size:1.3rem;font-weight:700;">{_fmt((weather or {{}}).get('temperature_c'), 1)}C</div>
            <div style="color:#888;font-size:0.78rem;">{escape(str((weather or {{}}).get('weather_main', 'Loading')))}</div>
            <div style="color:#666;font-size:0.7rem;">Wind {_fmt((weather or {{}}).get('wind_speed_ms'), 1)} m/s</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Mid row: Stats + Objectives ──
    mid1, mid2 = st.columns([1.2, 0.8])

    with mid1:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        s1, s2, s3 = st.columns(3)
        with s1:
            _ut_box("Indoor", f"{_fmt((latest or {}).get('temperature_c'), 1)}C",
                     f"{_fmt((latest or {}).get('humidity_pct'), 0)}% hum", "#25a7c8", 0)
        with s2:
            _ut_box("Motion", str(motion_count), "events / 24h", "#ffcc5c", 3)
        with s3:
            _ut_box("Ventilation", vent_text, "", vent_color, 4)

        _ut_box("Outfit", outfit_text, "Weather-based advice", "#ffcc5c", 2)

    with mid2:
        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
        _ut_objectives(objs)

        # Action buttons
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Start mood track", use_container_width=True):
                try:
                    _post("/api/music/play-mood", {
                        "mood": (weather or {}).get("weather_main", "Clear"),
                        "temperature_c": (weather or {}).get("temperature_c"),
                    })
                    st.success("Music started")
                except Exception:
                    st.error("Music unavailable")
        with b2:
            if st.button("Save weather", use_container_width=True):
                stored = _fetch("/api/weather/current", params={"store": "true"})
                st.success("Saved") if stored else st.warning("Not saved")

    # ── Forecast strip ──
    st.markdown('<div style="color:#666;font-family:\'Press Start 2P\',monospace;font-size:0.45rem;margin:12px 0 6px 0;">FORECAST RADAR</div>', unsafe_allow_html=True)
    _ut_forecast_row(fcast)

    # ── Companion decoration ──
    _companion_strip()

    # ── Charts (collapsed) ──
    with st.expander("Activity charts (24h)"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.plotly_chart(_spark(history_df, "temperature_c", "#25a7c8", "TEMP"), use_container_width=True)
        with c2:
            st.plotly_chart(_spark(history_df, "humidity_pct", "#24c08b", "HUMIDITY"), use_container_width=True)
        with c3:
            fig = go.Figure()
            if not history_df.empty and "motion_detected" in history_df.columns:
                mdf = history_df[history_df["motion_detected"] == True].copy()
                if not mdf.empty:
                    mdf["hour"] = mdf["timestamp"].dt.floor("h")
                    counts = mdf.groupby("hour").size().reset_index(name="events")
                    fig.add_trace(go.Bar(x=counts["hour"], y=counts["events"], marker_color="#d6a529"))
                else:
                    fig.add_annotation(text="No motion", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
            else:
                fig.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
            fig.update_layout(
                title=dict(text="MOTION", font=dict(family="Press Start 2P", size=8, color="#888")),
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=170, margin=dict(l=5, r=5, t=30, b=5),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
