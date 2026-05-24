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


def _health_rank(score):
    if score >= 90:
        return "S", "Perfect base", "All comfort systems are in a strong state."
    if score >= 80:
        return "A", "Healthy room", "Small changes only, the room is ready."
    if score >= 65:
        return "B", "Stable room", "Comfort is fine, but one signal can improve."
    if score >= 50:
        return "C", "Watch zone", "The room needs attention soon."
    return "D", "Recovery mode", "Fix comfort first: air, humidity, or temperature."


def _weather_mood_engine(weather, score):
    main = str((weather or {}).get("weather_main", "")).lower()
    temp = _num((weather or {}).get("temperature_c"))
    if "rain" in main or "drizzle" in main:
        return {
            "name": "Rain Quest",
            "trait": "Focus mode",
            "loadout": "Umbrella, calm playlist",
            "color": "#4ea5d9",
        }
    if temp is not None and temp >= 24:
        return {
            "name": "Solar Run",
            "trait": "High energy",
            "loadout": "Sunglasses, water, light clothes",
            "color": "#d6a529",
        }
    if temp is not None and temp <= 10:
        return {
            "name": "Frost Start",
            "trait": "Warm-up mode",
            "loadout": "Layers, jacket, slower morning",
            "color": "#7aa7d9",
        }
    if "clear" in main:
        return {
            "name": "Clear Boost",
            "trait": "Bright start",
            "loadout": "Sunglasses, outdoor break",
            "color": "#ffcc5c",
        }
    if "cloud" in main:
        return {
            "name": "Cloud Calm",
            "trait": "Steady focus",
            "loadout": "Light layer, relaxed playlist",
            "color": "#9aa6b2",
        }
    if score < 65:
        return {
            "name": "Recovery Quest",
            "trait": "Room first",
            "loadout": "Fix comfort before leaving",
            "color": "#e25555",
        }
    return {
        "name": "Neutral Day",
        "trait": "Balanced",
        "loadout": "Default outfit, default mood",
        "color": "#25a7c8",
    }


def _quest_objectives(score, latest, weather):
    objectives = []
    hum = _num((latest or {}).get("humidity_pct"))
    temp = _num((latest or {}).get("temperature_c"))
    co2 = _num((latest or {}).get("air_quality_index"))
    co2_source = (latest or {}).get("co2_source")
    main = str((weather or {}).get("weather_main", "")).lower()

    if score >= 85:
        objectives.append(("Room clear", True))
    else:
        objectives.append(("Improve comfort", False))

    if hum is None:
        objectives.append(("Humidity scan", False))
    elif 40 <= hum <= 60:
        objectives.append(("Humidity balanced", True))
    elif hum < 40:
        objectives.append(("Raise humidity", False))
    else:
        objectives.append(("Reduce humidity", False))

    if temp is None:
        objectives.append(("Temp scan", False))
    elif 20 <= temp <= 24:
        objectives.append(("Temp balanced", True))
    else:
        objectives.append(("Adjust temperature", False))

    if co2_source == "sensor" and co2 is not None:
        objectives.append(("Air clear", co2 < 800))

    if "rain" in main or "drizzle" in main:
        objectives.append(("Umbrella ready", False))
    elif weather:
        objectives.append(("Outdoor checked", True))
    else:
        objectives.append(("Outdoor scan", False))

    return objectives[:5]


def _render_health_and_mood(score, mood_engine, latest, weather):
    rank, rank_label, rank_detail = _health_rank(score)
    temp = _fmt((weather or {}).get("temperature_c"), 1, " C")
    hum = _fmt((latest or {}).get("humidity_pct"), 0, "%")

    st.markdown(f"""
    <div class="boss-card">
        <div class="dash-label">Room Health Rank</div>
        <div class="boss-rank">{escape(rank)}</div>
        <div class="dash-detail">{escape(rank_label)}. {escape(rank_detail)}</div>
        <div class="health-bar"><div class="health-fill" style="width:{score}%;"></div></div>
        <div class="dash-detail">Outdoor {escape(temp)} | Humidity {escape(hum)}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="boss-card" style="--mood-color:{mood_engine['color']};">
        <div class="mood-orb"></div>
        <div class="dash-label">Weather Mood Engine</div>
        <div class="dash-value" style="color:{mood_engine['color']};">{escape(mood_engine['name'])}</div>
        <div class="dash-detail">{escape(mood_engine['trait'])}</div>
        <div class="dash-detail">{escape(mood_engine['loadout'])}</div>
    </div>
    """, unsafe_allow_html=True)


def _tutorial_steps(score, mood_engine, objectives, briefing):
    rank, rank_label, _ = _health_rank(score)
    done_count = sum(1 for _, done in objectives if done)
    total = max(1, len(objectives))
    return [
        {
            "speaker": "Home Guide",
            "title": "Welcome to Home Base",
            "text": "This dashboard works like a tiny daily quest. Your goal is to keep the room healthy and prepare for the weather outside.",
        },
        {
            "speaker": "Comfort Scout",
            "title": "Check Your Room Rank",
            "text": f"Your current room rank is {rank}: {rank_label}. The score reacts to temperature, humidity, air quality, and recent motion.",
        },
        {
            "speaker": "Weather Oracle",
            "title": "Read The Mood",
            "text": f"Today is classified as {mood_engine['name']}. The mood engine turns outdoor weather into simple advice: {mood_engine['loadout']}.",
        },
        {
            "speaker": "Quest Log",
            "title": "Complete Objectives",
            "text": f"You have completed {done_count}/{total} comfort objectives. Green objectives are already safe, yellow ones need attention.",
        },
        {
            "speaker": "Morning Assistant",
            "title": "Use The Morning Briefing",
            "text": briefing,
        },
    ]


def _render_tutorial(score, mood_engine, objectives, briefing):
    steps = _tutorial_steps(score, mood_engine, objectives, briefing)
    if "home_tutorial_step" not in st.session_state:
        st.session_state["home_tutorial_step"] = 0
    step_index = max(0, min(len(steps) - 1, st.session_state["home_tutorial_step"]))
    step = steps[step_index]
    progress = int(((step_index + 1) / len(steps)) * 100)

    st.markdown(f"""
    <div class="routine-panel">
        <div class="dash-label">{escape(step["speaker"])} | Step {step_index + 1}/{len(steps)}</div>
        <div class="routine-text">{escape(step["title"])}</div>
        <div class="dash-detail">{escape(step["text"])}</div>
        <div class="health-bar"><div class="health-fill" style="width:{progress}%;"></div></div>
    </div>
    """, unsafe_allow_html=True)

    prev_col, next_col, skip_col = st.columns([1, 1, 1])
    with prev_col:
        if st.button("Back", use_container_width=True, disabled=step_index == 0):
            st.session_state["home_tutorial_step"] = max(0, step_index - 1)
            st.rerun()
    with next_col:
        label = "Unlock dashboard" if step_index == len(steps) - 1 else "Continue"
        if st.button(label, use_container_width=True):
            if step_index == len(steps) - 1:
                st.session_state["home_tutorial_done"] = True
            else:
                st.session_state["home_tutorial_step"] = min(len(steps) - 1, step_index + 1)
            st.rerun()
    with skip_col:
        if st.button("Skip", use_container_width=True):
            st.session_state["home_tutorial_done"] = True
            st.rerun()

    return step_index


def _render_morning_panel(briefing):
    st.markdown(f"""
    <div class="routine-panel">
        <div class="dash-label">Assistant says</div>
        <div class="routine-text">{escape(briefing)}</div>
        <div class="routine-grid">
            <span>Motion</span>
            <span>Advice</span>
            <span>Voice</span>
            <span>Music</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_tutorial_unlock(step_index, score, mood_engine, latest, weather, objectives, briefing):
    if step_index == 0:
        st.markdown('<div class="pixel-title">FIRST QUESTS</div>', unsafe_allow_html=True)
        _render_objectives(objectives[:3])
        _card("Goal", "Unlock Home Base", "Finish the guide to reveal the full dashboard.", "#ffcc5c")
    elif step_index == 1:
        st.markdown('<div class="pixel-title">UNLOCKED: HEALTH</div>', unsafe_allow_html=True)
        _render_health_and_mood(score, mood_engine, latest, weather)
    elif step_index == 2:
        st.markdown('<div class="pixel-title">UNLOCKED: WEATHER MOOD</div>', unsafe_allow_html=True)
        _card("Quest Mood", mood_engine["name"], mood_engine["trait"], mood_engine["color"])
        _card("Loadout", mood_engine["loadout"], "weather-based advice", "#ffcc5c")
    elif step_index == 3:
        st.markdown('<div class="pixel-title">UNLOCKED: OBJECTIVES</div>', unsafe_allow_html=True)
        _render_objectives(objectives)
    else:
        st.markdown('<div class="pixel-title">UNLOCKED: MORNING</div>', unsafe_allow_html=True)
        _render_morning_panel(briefing)


def _render_tutorial_reset_button():
    reset_col, _ = st.columns([1, 4])
    with reset_col:
        if st.button("Replay tutorial", use_container_width=True):
            st.session_state["home_tutorial_step"] = 0
            st.session_state["home_tutorial_done"] = False
            st.rerun()


def _render_objectives(objectives):
    rows = []
    for text, done in objectives:
        marker = "[OK]" if done else "[ ]"
        color = "#24c08b" if done else "#d6a529"
        rows.append(
            f'<span class="smart-pill" style="border-color:{color}; color:{color};">{marker} {escape(text)}</span>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


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
    mood_engine = _weather_mood_engine(weather, score)
    briefing = _morning_briefing(weather)
    outfit = _outfit_advice(weather)
    objectives = _quest_objectives(score, latest, weather)
    active_devices = [device for device in devices if device.get("is_active")]
    spotify_state = active_devices[0].get("name") if active_devices else "Waiting for music app"

    st.markdown("""
    <div class="pixel-shell">
        <div class="hero-band">
            <div>
                <div class="eyebrow">PLAYER 1: HOME</div>
                <h1>Home Base</h1>
                <p>Start with the guide, then unlock the full smart-home dashboard.</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tutorial_done = st.session_state.get("home_tutorial_done", False)
    if not tutorial_done:
        game_left, game_right = st.columns([1.15, 0.85])
        with game_left:
            st.markdown('<div class="pixel-title">TUTORIAL QUEST</div>', unsafe_allow_html=True)
            step_index = _render_tutorial(score, mood_engine, objectives, briefing)
        with game_right:
            _render_tutorial_unlock(step_index, score, mood_engine, latest, weather, objectives, briefing)
        st.caption("Complete the guide to unlock the full Home Base.")
        return

    _render_tutorial_reset_button()

    top_left, top_mid, top_right = st.columns([1, 1, 1])
    with top_left:
        st.markdown('<div class="pixel-title">HEALTH SCORE</div>', unsafe_allow_html=True)
        st.plotly_chart(_score_gauge(score, tone), use_container_width=True)
        _card("Room", comfort_label, ", ".join(reasons) if reasons else "Comfort OK", tone)
    with top_mid:
        st.markdown('<div class="pixel-title">MORNING QUEST</div>', unsafe_allow_html=True)
        _render_morning_panel(briefing)
        st.markdown('<div style="height: 6px;"></div>', unsafe_allow_html=True)
        controls = st.columns(2)
        with controls[0]:
            if st.button("Start mood track", use_container_width=True):
                try:
                    _post(
                        "/api/music/play-mood",
                        {"mood": (weather or {}).get("weather_main", "Clear"), "temperature_c": (weather or {}).get("temperature_c")},
                    )
                    st.success("Music started")
                except Exception:
                    st.error("Music is unavailable right now.")
        with controls[1]:
            if st.button("Save weather", use_container_width=True):
                stored = _fetch("/api/weather/current", params={"store": "true"})
                st.success("Saved") if stored else st.warning("Not saved")
    with top_right:
        st.markdown('<div class="pixel-title">WEATHER MOOD</div>', unsafe_allow_html=True)
        _card("Quest Mood", mood_engine["name"], mood_engine["trait"], mood_engine["color"])
        _card("Loadout", mood_engine["loadout"], "weather-based advice", "#ffcc5c")
        _card("Music", mood, spotify_state, mood_color)

    lower_left, lower_right = st.columns([1, 1])
    with lower_left:
        st.markdown('<div class="pixel-title">OBJECTIVES</div>', unsafe_allow_html=True)
        _render_objectives(objectives)
        st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="pixel-title">SIGNALS</div>', unsafe_allow_html=True)
        signal_cols = st.columns(3)
        with signal_cols[0]:
            _card("Indoor", f"{_fmt((latest or {}).get('temperature_c'), 1)} C", f"{_fmt((latest or {}).get('humidity_pct'), 0)}% humidity", "#24c08b")
        with signal_cols[1]:
            _card("Motion", str(motion_count), "events / 24h", "#ffcc5c")
        with signal_cols[2]:
            _card("Air", action, "ventilation state", "#25a7c8")
    with lower_right:
        st.markdown('<div class="pixel-title">TODAY LOADOUT</div>', unsafe_allow_html=True)
        _card("Outdoor", f"{_fmt((weather or {}).get('temperature_c'), 1)} C", (weather or {}).get("weather_main", "Unavailable"), "#d6a529")
        _card("Wear", outfit, "", "#ffcc5c")
        _render_health_and_mood(score, mood_engine, latest, weather)

    with st.expander("Show activity charts"):
        chart_cols = st.columns(3)
        with chart_cols[0]:
            st.plotly_chart(_mini_line(history_df, "temperature_c", "#25a7c8", "Indoor temperature"), use_container_width=True)
        with chart_cols[1]:
            st.plotly_chart(_mini_line(history_df, "humidity_pct", "#24c08b", "Humidity"), use_container_width=True)
        with chart_cols[2]:
            st.plotly_chart(_motion_timeline(history_df), use_container_width=True)

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
