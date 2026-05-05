"""
Streamlit dashboard entry point.
"""

import os
import sys

import streamlit as st

st.set_page_config(
    page_title="Weather Station",
    page_icon="cloud",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

div[data-testid="stSidebarNav"] {
    display: none;
}

section[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}

section[data-testid="stSidebar"] > div {
    padding-top: 0.75rem;
}

[data-testid="stSidebarUserContent"] {
    padding: 1rem 1.25rem 1.25rem 1.25rem;
}

.main {
    background: #0f172a;
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1280px;
}

[data-testid="metric-container"] {
    background: #1e293b;
    border-radius: 8px;
    padding: 12px 16px;
    border: 1px solid #334155;
}

h1 {
    letter-spacing: 0;
    font-weight: 700;
    margin-bottom: 0.35rem;
}

h3 {
    margin-top: 1.25rem;
    margin-bottom: 0.75rem;
}

div[role="radiogroup"] label {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0.35rem 0.5rem;
    margin-bottom: 0.15rem;
}

div[role="radiogroup"] label:hover {
    background: #1e293b;
    border-color: #334155;
}

.sidebar-brand {
    padding: 0.75rem 0 1rem 0;
}

.sidebar-brand-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #f8fafc;
    line-height: 1.2;
}

.sidebar-brand-subtitle {
    font-size: 0.78rem;
    color: #94a3b8;
    margin-top: 0.25rem;
}

.sidebar-section-label {
    color: #64748b;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 1rem 0 0.35rem 0;
}

.sidebar-footer {
    color: #475569;
    font-size: 0.72rem;
    line-height: 1.35;
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-brand-title">Weather Station</div>
        <div class="sidebar-brand-subtitle">Cloud & Advanced Analytics</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-label">Views</div>', unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["Real-Time", "History", "Ask Data"],
        label_visibility="collapsed",
    )

    st.markdown('<div class="sidebar-section-label">Controls</div>', unsafe_allow_html=True)

    if st.button("Refresh now", use_container_width=True):
        st.rerun()

    auto_refresh = st.toggle("Auto-refresh (60s)", value=False)
    if auto_refresh:
        import time
        st.caption("Page will refresh every 60 seconds.")
        time.sleep(60)
        st.rerun()

    st.markdown("""
    <div class="sidebar-footer">
        Data from BigQuery, OpenWeatherMap, and Gemini.
    </div>
    """, unsafe_allow_html=True)

sys.path.insert(0, os.path.dirname(__file__))

if page == "Real-Time":
    from pages.current import render
elif page == "History":
    from pages.history import render
else:
    from pages.ask import render

render()
