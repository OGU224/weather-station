"""
Live Map page — Undertale RPG sensor dashboard with pixel companions.
"""

import os
import sys
from dataclasses import asdict
from datetime import datetime
from html import escape

import requests
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "https://weather-middleware-387666611940.europe-west1.run.app")
HUMIDITY_ALERT = 40

# ── Companion SVG sprites ─────────────────────────────────────────────────────

GHOST_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="6" y="1" width="4" height="1" fill="#fff"/><rect x="4" y="2" width="8" height="1" fill="#fff"/>
<rect x="3" y="3" width="10" height="1" fill="#fff"/><rect x="2" y="4" width="12" height="2" fill="#fff"/>
<rect x="2" y="6" width="2" height="1" fill="#fff"/><rect x="4" y="6" width="1" height="1" fill="#111"/><rect x="5" y="6" width="5" height="1" fill="#fff"/><rect x="10" y="6" width="1" height="1" fill="#111"/><rect x="11" y="6" width="3" height="1" fill="#fff"/>
<rect x="2" y="7" width="2" height="1" fill="#fff"/><rect x="4" y="7" width="2" height="1" fill="#111"/><rect x="6" y="7" width="4" height="1" fill="#fff"/><rect x="10" y="7" width="2" height="1" fill="#111"/><rect x="12" y="7" width="2" height="1" fill="#fff"/>
<rect x="2" y="8" width="12" height="1" fill="#fff"/><rect x="2" y="9" width="5" height="1" fill="#fff"/><rect x="7" y="9" width="2" height="1" fill="#111"/><rect x="9" y="9" width="5" height="1" fill="#fff"/>
<rect x="2" y="10" width="12" height="2" fill="#fff"/>
<rect x="2" y="12" width="3" height="1" fill="#fff"/><rect x="6" y="12" width="4" height="1" fill="#fff"/><rect x="11" y="12" width="3" height="1" fill="#fff"/>
<rect x="2" y="13" width="2" height="1" fill="#fff"/><rect x="6" y="13" width="2" height="1" fill="#fff"/><rect x="11" y="13" width="2" height="1" fill="#fff"/>
</svg>"""

SKULL_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="5" y="1" width="6" height="1" fill="#fff"/><rect x="3" y="2" width="10" height="1" fill="#fff"/><rect x="2" y="3" width="12" height="1" fill="#fff"/>
<rect x="2" y="4" width="2" height="1" fill="#fff"/><rect x="4" y="4" width="4" height="1" fill="#111"/><rect x="8" y="4" width="1" height="1" fill="#fff"/><rect x="9" y="4" width="4" height="1" fill="#111"/><rect x="13" y="4" width="1" height="1" fill="#fff"/>
<rect x="2" y="5" width="2" height="1" fill="#fff"/><rect x="4" y="5" width="1" height="1" fill="#111"/><rect x="5" y="5" width="2" height="1" fill="#0df"/><rect x="7" y="5" width="2" height="1" fill="#111"/><rect x="9" y="5" width="1" height="1" fill="#111"/><rect x="10" y="5" width="2" height="1" fill="#0df"/><rect x="12" y="5" width="2" height="1" fill="#fff"/>
<rect x="2" y="6" width="2" height="1" fill="#fff"/><rect x="4" y="6" width="4" height="1" fill="#111"/><rect x="8" y="6" width="1" height="1" fill="#fff"/><rect x="9" y="6" width="4" height="1" fill="#111"/><rect x="13" y="6" width="1" height="1" fill="#fff"/>
<rect x="2" y="7" width="12" height="1" fill="#fff"/><rect x="2" y="8" width="5" height="1" fill="#fff"/><rect x="7" y="8" width="2" height="1" fill="#111"/><rect x="9" y="8" width="5" height="1" fill="#fff"/>
<rect x="3" y="10" width="10" height="1" fill="#fff"/><rect x="4" y="11" width="8" height="1" fill="#6bf"/><rect x="3" y="12" width="10" height="2" fill="#6bf"/>
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
</svg>"""

ROBOT_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="7" y="0" width="2" height="1" fill="#ff0"/><rect x="7" y="1" width="2" height="1" fill="#999"/>
<rect x="3" y="2" width="10" height="1" fill="#999"/><rect x="3" y="3" width="10" height="6" fill="#222"/>
<rect x="3" y="3" width="1" height="6" fill="#999"/><rect x="12" y="3" width="1" height="6" fill="#999"/>
<rect x="5" y="5" width="2" height="2" fill="#0c0"/><rect x="9" y="5" width="2" height="2" fill="#0c0"/>
<rect x="5" y="8" width="6" height="1" fill="#0c0"/><rect x="3" y="9" width="10" height="1" fill="#999"/>
<rect x="4" y="10" width="8" height="3" fill="#999"/><rect x="7" y="11" width="2" height="1" fill="#f22"/>
<rect x="4" y="13" width="2" height="2" fill="#999"/><rect x="9" y="13" width="2" height="2" fill="#999"/>
</svg>"""

MUSHROOM_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="6" y="0" width="6" height="1" fill="#f22"/><rect x="4" y="1" width="10" height="1" fill="#f22"/>
<rect x="2" y="2" width="2" height="1" fill="#f22"/><rect x="4" y="2" width="2" height="1" fill="#fff"/><rect x="6" y="2" width="5" height="1" fill="#f22"/><rect x="11" y="2" width="2" height="1" fill="#fff"/><rect x="13" y="2" width="2" height="1" fill="#f22"/>
<rect x="2" y="3" width="14" height="1" fill="#f22"/><rect x="1" y="4" width="14" height="2" fill="#f22"/>
<rect x="2" y="6" width="12" height="2" fill="#fec"/>
<rect x="3" y="8" width="2" height="2" fill="#111"/><rect x="5" y="8" width="3" height="2" fill="#fec"/><rect x="8" y="8" width="2" height="2" fill="#111"/><rect x="10" y="8" width="3" height="2" fill="#fec"/>
<rect x="2" y="9" width="1" height="1" fill="#f8a"/><rect x="12" y="9" width="1" height="1" fill="#f8a"/>
<rect x="4" y="11" width="8" height="1" fill="#fec"/><rect x="5" y="12" width="6" height="1" fill="#fec"/>
<rect x="4" y="13" width="8" height="2" fill="#a52"/>
</svg>"""

FLOWER_SVG = """<svg width="{s}" height="{s}" viewBox="0 0 16 16" style="image-rendering:pixelated;">
<rect x="6" y="0" width="4" height="1" fill="#ff0"/><rect x="3" y="1" width="10" height="1" fill="#ff0"/>
<rect x="2" y="2" width="3" height="1" fill="#ff0"/><rect x="5" y="2" width="6" height="1" fill="#fec"/><rect x="11" y="2" width="3" height="1" fill="#ff0"/>
<rect x="2" y="3" width="1" height="1" fill="#ff0"/><rect x="3" y="3" width="10" height="1" fill="#fec"/><rect x="13" y="3" width="1" height="1" fill="#ff0"/>
<rect x="2" y="4" width="1" height="1" fill="#ff0"/><rect x="3" y="4" width="2" height="1" fill="#fec"/><rect x="5" y="4" width="2" height="1" fill="#111"/><rect x="7" y="4" width="2" height="1" fill="#fec"/><rect x="9" y="4" width="2" height="1" fill="#111"/><rect x="11" y="4" width="2" height="1" fill="#fec"/><rect x="13" y="4" width="1" height="1" fill="#ff0"/>
<rect x="2" y="5" width="1" height="1" fill="#ff0"/><rect x="3" y="5" width="10" height="1" fill="#fec"/><rect x="13" y="5" width="1" height="1" fill="#ff0"/>
<rect x="3" y="6" width="3" height="1" fill="#ff0"/><rect x="6" y="6" width="4" height="1" fill="#111"/><rect x="10" y="6" width="3" height="1" fill="#ff0"/>
<rect x="7" y="7" width="2" height="4" fill="#0a0"/><rect x="4" y="11" width="8" height="2" fill="#a52"/>
</svg>"""

ALL_COMPANIONS = [
    ("Ghost", GHOST_SVG), ("Skull", SKULL_SVG), ("Flower", FLOWER_SVG),
    ("Cat", CAT_SVG), ("Robot", ROBOT_SVG), ("Mushroom", MUSHROOM_SVG),
]


def _companion(idx, size=48):
    _, svg = ALL_COMPANIONS[idx % len(ALL_COMPANIONS)]
    return svg.format(s=size)


# ── Data fetching ─────────────────────────────────────────────────────────────

def _fetch(path, params=None):
    try:
        r = requests.get(f"{MIDDLEWARE_URL}{path}", params=params, timeout=8)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    return None


def _fetch_latest_sensor():
    sensor = _fetch("/api/sensors/latest")
    if sensor:
        return sensor
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
            "air_quality_label": row.get("air_quality_label"),
            "co2_source": row.get("co2_source"),
            "motion_detected": row.get("motion_detected"),
        }
    except Exception:
        return None


def _fetch_weather():
    weather = _fetch("/api/weather/current")
    if weather:
        return weather
    try:
        from services.weather_service import WeatherService
        w = WeatherService().get_current_weather()
        return w.to_dict() if w else None
    except Exception:
        return None


def _fetch_forecast(days=5):
    fc = _fetch("/api/weather/forecast", params={"days": days})
    if fc:
        return fc
    try:
        from dataclasses import asdict
        from services.weather_service import WeatherService
        return [asdict(d) for d in WeatherService().get_forecast(days=days)]
    except Exception:
        return []


def _num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _fmt(v, d=1, s=""):
    v = _num(v)
    return f"{v:.{d}f}{s}" if v is not None else "--"


def _aqi_label(val):
    v = _num(val)
    if v is None:
        return "--", "#666"
    if v < 800:
        return "Good", "#24c08b"
    if v < 1200:
        return "Moderate", "#d6a529"
    return "Poor", "#e25555"


def _co2_rows(df):
    if df.empty or "air_quality_index" not in df.columns:
        return df.iloc[0:0] if hasattr(df, "iloc") else df
    co2_df = df[df["air_quality_index"].notna()].copy()
    if "co2_source" in co2_df.columns:
        sensor_rows = co2_df[co2_df["co2_source"] == "sensor"]
        if not sensor_rows.empty:
            return sensor_rows
    return co2_df


# ── UI components ─────────────────────────────────────────────────────────────

def _ut_stat(label, value, detail="", color="#25a7c8", companion_idx=None):
    sprite = ""
    if companion_idx is not None:
        sprite = f'<div style="position:absolute;bottom:6px;right:8px;opacity:0.2;">{_companion(companion_idx, 28)}</div>'
    st.markdown(f"""
    <div style="background:#0a0a0a;border:3px solid #2e3b47;padding:16px 18px;position:relative;margin-bottom:10px;min-height:100px;">
        {sprite}
        <div style="color:#666;font-family:'Press Start 2P',monospace;font-size:0.42rem;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:8px;">{escape(label)}</div>
        <div style="color:{color};font-size:1.6rem;font-weight:700;line-height:1;">{escape(str(value))}</div>
        <div style="color:#777;font-size:0.8rem;margin-top:6px;">{escape(detail)}</div>
    </div>
    """, unsafe_allow_html=True)


def _ut_hp(label, value, max_val=100, color="#24c08b"):
    pct = max(0, min(100, int(value / max_val * 100))) if max_val > 0 else 0
    st.markdown(f"""
    <div style="margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.42rem;">{escape(label)}</span>
            <span style="color:#aaa;font-size:0.75rem;">{value} / {max_val}</span>
        </div>
        <div style="height:14px;background:#440000;border:2px solid {color};">
            <div style="height:100%;width:{pct}%;background:{color};transition:width 0.3s;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _ut_dialogue(speaker, text, companion_idx=0):
    st.markdown(f"""
    <div style="display:flex;align-items:flex-start;gap:16px;background:#000;border:3px solid #fff;padding:16px 18px;margin-bottom:14px;">
        <div style="flex-shrink:0;margin-top:4px;">{_companion(companion_idx, 56)}</div>
        <div style="flex:1;">
            <div style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.48rem;margin-bottom:8px;">{escape(speaker)}</div>
            <div style="color:#fff;font-size:0.9rem;line-height:1.55;">* {escape(text)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _ut_section(title):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:20px 0 10px 0;">
        <div style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.52rem;letter-spacing:0.1em;">{escape(title)}</div>
        <div style="flex:1;height:2px;background:#2e3b47;"></div>
    </div>
    """, unsafe_allow_html=True)


def _ut_weather_card(weather):
    if not weather:
        st.markdown("""
        <div style="background:#0a0a0a;border:3px solid #2e3b47;padding:24px;text-align:center;min-height:200px;display:flex;align-items:center;justify-content:center;">
            <div style="color:#666;font-size:0.85rem;">* Outdoor data unavailable</div>
        </div>
        """, unsafe_allow_html=True)
        return

    icon = weather.get("weather_icon", "")
    icon_url = f"https://openweathermap.org/img/wn/{icon}@2x.png" if icon else ""
    main = weather.get("weather_main", "--")
    desc = str(weather.get("weather_description", "")).capitalize()
    temp = _fmt(weather.get("temperature_c"), 1)
    feels = _fmt(weather.get("feels_like_c"), 1)
    wind = _fmt(weather.get("wind_speed_ms"), 1)
    hum = _fmt(weather.get("humidity_pct"), 0)
    city = weather.get("city", "Outdoor")

    st.markdown(f"""
    <div style="background:#0a0a0a;border:3px solid #2e3b47;padding:20px;position:relative;">
        <div style="display:flex;align-items:center;gap:20px;">
            <div style="text-align:center;">
                {"<img src='" + icon_url + "' width='64' style='display:block;margin:0 auto;'/>" if icon_url else ""}
                <div style="color:#888;font-size:0.75rem;margin-top:2px;">{escape(desc)}</div>
            </div>
            <div style="flex:1;">
                <div style="color:#666;font-family:'Press Start 2P',monospace;font-size:0.42rem;margin-bottom:6px;">{escape(city).upper()}</div>
                <div style="color:#fb923c;font-size:2.2rem;font-weight:700;line-height:1;">{temp}C</div>
                <div style="color:#888;font-size:0.82rem;margin-top:6px;">Feels {feels}C</div>
            </div>
        </div>
        <div style="display:flex;gap:12px;margin-top:16px;">
            <div style="flex:1;background:#111;border:2px solid #2e3b47;padding:10px;text-align:center;">
                <div style="color:#666;font-family:'Press Start 2P',monospace;font-size:0.35rem;margin-bottom:4px;">WIND</div>
                <div style="color:#25a7c8;font-size:1.1rem;font-weight:700;">{wind}</div>
                <div style="color:#666;font-size:0.65rem;">m/s</div>
            </div>
            <div style="flex:1;background:#111;border:2px solid #2e3b47;padding:10px;text-align:center;">
                <div style="color:#666;font-family:'Press Start 2P',monospace;font-size:0.35rem;margin-bottom:4px;">HUMIDITY</div>
                <div style="color:#24c08b;font-size:1.1rem;font-weight:700;">{hum}</div>
                <div style="color:#666;font-size:0.65rem;">%</div>
            </div>
            <div style="flex:1;background:#111;border:2px solid #2e3b47;padding:10px;text-align:center;">
                <div style="color:#666;font-family:'Press Start 2P',monospace;font-size:0.35rem;margin-bottom:4px;">CONDITION</div>
                <div style="color:#d6a529;font-size:1.1rem;font-weight:700;">{escape(main)}</div>
                <div style="color:#666;font-size:0.65rem;">now</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _ut_forecast_strip(forecasts):
    if not forecasts:
        st.caption("* No forecast data yet.")
        return
    cols = st.columns(min(5, len(forecasts)))
    for i, fc in enumerate(forecasts[:5]):
        date = str(fc.get("date", ""))[-5:]
        t_max = round(_num(fc.get("temp_max"), 0), 1)
        t_min = round(_num(fc.get("temp_min"), 0), 1)
        main = str(fc.get("weather_main", ""))
        icon = fc.get("weather_icon", "")
        icon_url = f"https://openweathermap.org/img/wn/{icon}@2x.png" if icon else ""
        rain = "rain" in main.lower() or "drizzle" in main.lower()
        border_color = "#4ea5d9" if rain else "#2e3b47"
        rain_tag = "<div style='color:#4ea5d9;font-size:0.5rem;margin-top:2px;'>rain</div>" if rain else ""
        icon_tag = f"<img src='{icon_url}' width='32' style='margin:4px auto;display:block;'/>" if icon_url else f"<div style='color:#fff;font-size:0.75rem;margin:8px 0;'>{escape(main[:7])}</div>"
        with cols[i]:
            st.markdown(f"""
            <div style="background:#0a0a0a;border:3px solid {border_color};padding:12px 8px;text-align:center;">
                <div style="color:#888;font-size:0.65rem;margin-bottom:4px;">{date}</div>
                {icon_tag}
                <div style="color:#0df;font-size:0.9rem;font-weight:700;">{t_max}C</div>
                <div style="color:#555;font-size:0.65rem;">{t_min}C</div>
                {rain_tag}
            </div>
            """, unsafe_allow_html=True)


def _companion_divider():
    html = '<div style="display:flex;justify-content:center;gap:20px;padding:6px 0;margin:8px 0;opacity:0.4;">'
    for i in range(6):
        html += _companion(i, 28)
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ── Main render ───────────────────────────────────────────────────────────────

def render():
    with st.spinner("* Scanning all sensors..."):
        sensor = _fetch_latest_sensor()
        weather = _fetch_weather()
        forecast = _fetch_forecast()

    # ── Hero banner ──
    st.markdown(f"""
    <div style="background:#000;border:3px solid #fff;padding:18px 22px;margin-bottom:16px;position:relative;overflow:hidden;">
        <div style="position:absolute;top:8px;right:14px;opacity:0.12;display:flex;gap:10px;">
            {_companion(4, 48)}{_companion(1, 48)}{_companion(5, 48)}
        </div>
        <div style="color:#ff0;font-family:'Press Start 2P',monospace;font-size:0.5rem;margin-bottom:8px;">LIVE MAP</div>
        <div style="color:#fff;font-size:1.6rem;font-weight:700;">Sensor Zone</div>
        <div style="color:#888;font-size:0.88rem;margin-top:4px;">Real-time indoor and outdoor scan.</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Alerts ──
    if sensor:
        hum = _num(sensor.get("humidity_pct"))
        co2_src = sensor.get("co2_source")
        aqi = _num(sensor.get("air_quality_index"))
        if hum is not None and hum < HUMIDITY_ALERT:
            _ut_dialogue("Robot", f"Warning! Humidity at {int(hum)}% — below {HUMIDITY_ALERT}% threshold.", 4)
        aqi_lbl, _ = _aqi_label(aqi)
        if co2_src == "sensor" and aqi_lbl == "Poor":
            _ut_dialogue("Mushroom", f"CO2 is at {int(aqi)} ppm. Please ventilate!", 5)

    # ── Indoor section ──
    _ut_section("INDOOR BASE")

    if sensor:
        temp_in = _num(sensor.get("temperature_c"))
        hum_in = _num(sensor.get("humidity_pct"))
        aqi_val = _num(sensor.get("air_quality_index"))
        co2_src = sensor.get("co2_source")
        motion = bool(sensor.get("motion_detected", False))
        aqi_lbl, aqi_color = _aqi_label(aqi_val) if co2_src == "sensor" else ("--", "#666")
        hum_color = "#e25555" if hum_in is not None and hum_in < HUMIDITY_ALERT else "#24c08b"

        # HP bars
        hp1, hp2 = st.columns(2)
        with hp1:
            _ut_hp("TEMP", round(temp_in) if temp_in else 0, 40, "#25a7c8")
        with hp2:
            _ut_hp("HUM", round(hum_in) if hum_in else 0, 100, hum_color)

        st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

        # Stat cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            _ut_stat("Temperature", f"{_fmt(temp_in, 1)}C", "indoor", "#25a7c8", 0)
        with c2:
            _ut_stat("Humidity", f"{_fmt(hum_in, 0)}%", "indoor", hum_color, 5)
        with c3:
            co2_detail = f"{_fmt(aqi_val, 0)} ppm" if co2_src == "sensor" else "not measured"
            _ut_stat("CO2", aqi_lbl, co2_detail, aqi_color, 4)
        with c4:
            _ut_stat("Motion", "Yes" if motion else "No", "detected now", "#fb923c" if motion else "#666", 3)
    else:
        st.markdown("""
        <div style="background:#0a0a0a;border:3px solid #2e3b47;padding:24px;text-align:center;">
            <div style="color:#666;font-size:0.85rem;">* Waiting for indoor sensor data...</div>
        </div>
        """, unsafe_allow_html=True)

    _companion_divider()

    # ── Outdoor section ──
    _ut_section("OUTDOOR SCAN")

    _ut_weather_card(weather)

    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

    # ── Forecast section ──
    _ut_section("FORECAST RADAR")

    if forecast:
        # Companion-narrated weather tip
        w_main = str((weather or {}).get("weather_main", "")).lower()
        if any("rain" in str(f.get("weather_main", "")).lower() for f in forecast):
            _ut_dialogue("Ghost", "Rain is coming... Don't forget your umbrella.", 0)
        elif "clear" in w_main:
            _ut_dialogue("Flower", "Clear skies ahead! A perfect day to bloom.", 2)
        else:
            _ut_dialogue("Cat", "Weather looks calm. Nothing to worry about.", 3)

        _ut_forecast_strip(forecast)
    else:
        st.markdown("""
        <div style="background:#0a0a0a;border:3px solid #2e3b47;padding:24px;text-align:center;">
            <div style="color:#666;font-size:0.85rem;">* No forecast data available yet.</div>
        </div>
        """, unsafe_allow_html=True)

    _companion_divider()

    # ── Activity charts ──
    _ut_section("ACTIVITY CHARTS")

    sensor_history = _fetch("/api/sensors/history", params={"hours": 24})
    if sensor_history:
        import pandas as pd
        import plotly.graph_objects as go

        df = pd.DataFrame(sensor_history)
        for col in ["temperature_c", "humidity_pct", "air_quality_index"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
            df = df.dropna(subset=["timestamp"]).sort_values("timestamp")

        if not df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig = go.Figure()
                if "temperature_c" in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df["timestamp"], y=df["temperature_c"],
                        mode="lines", fill="tozeroy",
                        line=dict(color="#25a7c8", width=2),
                    ))
                fig.update_layout(
                    title=dict(text="TEMPERATURE 24H", font=dict(family="Press Start 2P", size=8, color="#888")),
                    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    height=220, margin=dict(l=5, r=5, t=35, b=5), showlegend=False,
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, title="C"),
                )
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                fig = go.Figure()
                if "humidity_pct" in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df["timestamp"], y=df["humidity_pct"],
                        mode="lines", fill="tozeroy",
                        line=dict(color="#24c08b", width=2),
                    ))
                    fig.add_hline(y=40, line_dash="dash", line_color="#e25555",
                                 annotation_text="Alert 40%", annotation_font_color="#e25555")
                fig.update_layout(
                    title=dict(text="HUMIDITY 24H", font=dict(family="Press Start 2P", size=8, color="#888")),
                    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    height=220, margin=dict(l=5, r=5, t=35, b=5), showlegend=False,
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, title="%", range=[0, 100]),
                )
                st.plotly_chart(fig, use_container_width=True)

            c3, c4 = st.columns(2)
            with c3:
                fig = go.Figure()
                if "air_quality_index" in df.columns:
                    co2_df = _co2_rows(df)
                    if not co2_df.empty and co2_df["air_quality_index"].notna().any():
                        co2_values = co2_df["air_quality_index"]
                        fig.add_trace(go.Scatter(
                            x=co2_df["timestamp"],
                            y=co2_values,
                            mode="lines+markers",
                            line=dict(color="#24c08b", width=3),
                            marker=dict(size=5, color="#24c08b", line=dict(color="#ffffff", width=1)),
                            fill="tozeroy",
                            fillcolor="rgba(36,192,139,0.12)",
                        ))
                        fig.add_hline(y=800, line_dash="dash", line_color="#d6a529")
                        fig.add_hline(y=1200, line_dash="dash", line_color="#e25555")
                        max_value = float(co2_values.max())
                        fig.update_yaxes(range=[0, max(1000, max_value + 150)])
                    else:
                        fig.add_annotation(text="No CO2 sensor data", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
                else:
                    fig.add_annotation(text="No CO2 data", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
                fig.update_layout(
                    title=dict(text="CO2 24H", font=dict(family="Press Start 2P", size=8, color="#888")),
                    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    height=220, margin=dict(l=5, r=5, t=35, b=5), showlegend=False,
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, title="ppm"),
                )
                st.plotly_chart(fig, use_container_width=True)

            with c4:
                fig = go.Figure()
                if "motion_detected" in df.columns:
                    mdf = df[df["motion_detected"] == True].copy()
                    if not mdf.empty:
                        mdf["hour"] = mdf["timestamp"].dt.floor("h")
                        counts = mdf.groupby("hour").size().reset_index(name="events")
                        fig.add_trace(go.Bar(x=counts["hour"], y=counts["events"], marker_color="#d6a529"))
                    else:
                        fig.add_annotation(text="No motion detected", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
                else:
                    fig.add_annotation(text="No motion data", x=0.5, y=0.5, showarrow=False, font=dict(color="#555"))
                fig.update_layout(
                    title=dict(text="MOTION 24H", font=dict(family="Press Start 2P", size=8, color="#888")),
                    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    height=220, margin=dict(l=5, r=5, t=35, b=5), showlegend=False,
                    xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, title="events"),
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("* No sensor history available for charts.")
    else:
        st.caption("* Could not load sensor history for charts.")

    _companion_divider()

    st.caption(f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}")
