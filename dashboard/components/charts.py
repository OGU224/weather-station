"""
Reusable Plotly chart and card helpers for the Streamlit dashboard.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PLOTLY_TEMPLATE = "plotly_dark"
ALERT_HUMIDITY_THRESHOLD = 40
COLOR_INDOOR_TEMP = "#38bdf8"
COLOR_OUTDOOR_TEMP = "#fb923c"
COLOR_HUMIDITY = "#34d399"
COLOR_ALERT = "#f87171"
COLOR_AQI_GOOD = "#34d399"
COLOR_AQI_MODERATE = "#fbbf24"
COLOR_AQI_BAD = "#f87171"

OWM_ICON_DESCRIPTIONS = {
    "Clear": "Sunny",
    "Clouds": "Cloudy",
    "Rain": "Rain",
    "Drizzle": "Drizzle",
    "Thunderstorm": "Storm",
    "Snow": "Snow",
    "Mist": "Mist",
    "Fog": "Fog",
    "Haze": "Haze",
    "Smoke": "Smoke",
    "Dust": "Dust",
    "Tornado": "Tornado",
}


def weather_emoji(weather_main: str) -> str:
    """Return a readable fallback label for a weather condition string."""
    return OWM_ICON_DESCRIPTIONS.get(weather_main, "Weather")


def _empty_chart(title: str, message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(color="#94a3b8", size=14),
    )
    fig.update_layout(
        title=title,
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40, b=0),
        height=300,
    )
    return fig


def temperature_chart(
    df: pd.DataFrame,
    indoor_col="temperature_c",
    outdoor_col=None,
    title="Temperature (C)",
) -> go.Figure:
    """Line chart for indoor or outdoor temperature over time."""
    if "timestamp" not in df.columns or indoor_col not in df.columns:
        return _empty_chart(title, "No temperature data available")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df[indoor_col],
        name="Temperature",
        mode="lines+markers",
        line=dict(color=COLOR_INDOOR_TEMP, width=2),
        marker=dict(size=4),
    ))
    if outdoor_col and outdoor_col in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df[outdoor_col],
            name="Outdoor",
            mode="lines+markers",
            line=dict(color=COLOR_OUTDOOR_TEMP, width=2, dash="dot"),
            marker=dict(size=4),
        ))
    fig.update_layout(
        title=title,
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="C",
        xaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=40, b=0),
        height=300,
    )
    return fig


def humidity_chart(df: pd.DataFrame, col="humidity_pct", title="Humidity (%)") -> go.Figure:
    """Line chart for humidity with an alert threshold line."""
    if "timestamp" not in df.columns or col not in df.columns:
        return _empty_chart(title, "No humidity data available")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df[col],
        name="Humidity",
        mode="lines+markers",
        fill="tozeroy",
        line=dict(color=COLOR_HUMIDITY, width=2),
        marker=dict(size=4),
    ))
    fig.add_hline(
        y=ALERT_HUMIDITY_THRESHOLD,
        line_dash="dash",
        line_color=COLOR_ALERT,
        annotation_text="Alert threshold (40%)",
        annotation_position="top right",
        annotation_font_color=COLOR_ALERT,
    )
    fig.update_layout(
        title=title,
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="%",
        yaxis_range=[0, 100],
        xaxis_title="",
        margin=dict(l=0, r=0, t=40, b=0),
        height=300,
    )
    return fig


def air_quality_chart(
    df: pd.DataFrame,
    col="air_quality_index",
    title="Air Quality Index (CO2 ppm)",
) -> go.Figure:
    """Bar chart for air quality, colored by level."""
    if "timestamp" not in df.columns or col not in df.columns:
        return _empty_chart(title, "No air quality data available")

    def aqi_color(val):
        if val < 50:
            return COLOR_AQI_GOOD
        if val < 100:
            return COLOR_AQI_MODERATE
        return COLOR_AQI_BAD

    colors = df[col].apply(aqi_color).tolist()
    fig = go.Figure(go.Bar(
        x=df["timestamp"],
        y=df[col],
        marker_color=colors,
        name="AQI",
    ))
    fig.update_layout(
        title=title,
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="ppm",
        xaxis_title="",
        margin=dict(l=0, r=0, t=40, b=0),
        height=300,
    )
    return fig


def forecast_cards(forecasts: list) -> None:
    """Render the forecast as styled cards in a Streamlit row."""
    cols = st.columns(len(forecasts))
    for col, day in zip(cols, forecasts):
        fallback_label = weather_emoji(day.get("weather_main", ""))
        icon_code = day.get("weather_icon", "")
        icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png" if icon_code else ""
        date_label = day.get("date", "")
        temp_min = day.get("temp_min", "--")
        temp_max = day.get("temp_max", "--")
        description = day.get("weather_description", fallback_label).capitalize()

        with col:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #1e293b, #0f172a);
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 14px 10px;
                text-align: center;
                margin: 4px;
                min-height: 150px;
            ">
                <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px;">
                    {date_label}
                </div>
                {"<img src='" + icon_url + "' width='50' style='display:block;margin:0 auto;'/>" if icon_url else f"<div style='font-size:1rem;color:#e2e8f0;margin:16px 0;'>{fallback_label}</div>"}
                <div style="font-size: 0.8rem; color: #cbd5e1; margin: 6px 0 2px 0;">
                    {description}
                </div>
                <div style="font-size: 1rem; font-weight: 700; color: #38bdf8;">
                    {temp_max} C <span style="color:#64748b; font-weight:400;">{temp_min} C</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


def metric_card(
    label: str,
    value: str,
    unit: str = "",
    delta: str = None,
    icon: str = "",
    color: str = "#38bdf8",
) -> str:
    """Return HTML for a styled metric card."""
    delta_html = ""
    if delta is not None:
        delta_color = "#34d399" if not delta.startswith("-") else COLOR_ALERT
        delta_html = f'<div style="font-size:0.75rem;color:{delta_color};margin-top:2px;">{delta}</div>'

    return f"""
    <div style="
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 18px 16px;
        text-align: center;
        min-height: 130px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    ">
        <div style="font-size: 1.6rem; margin-bottom: 4px;">{icon}</div>
        <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;
                    letter-spacing: 0.08em; margin-bottom: 6px;">{label}</div>
        <div style="font-size: 1.8rem; font-weight: 700; color: {color};">
            {value}<span style="font-size:1rem; color:#94a3b8;"> {unit}</span>
        </div>
        {delta_html}
    </div>
    """
