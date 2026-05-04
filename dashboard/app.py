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

section[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}

.main {
    background: #0f172a;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

[data-testid="metric-container"] {
    background: #1e293b;
    border-radius: 12px;
    padding: 12px 16px;
    border: 1px solid #334155;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0 1.5rem 0;">
        <div style="font-size: 2.5rem;">Cloud</div>
        <div style="font-size: 1.1rem; font-weight: 700; color: #f1f5f9;">Weather Station</div>
        <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">Cloud & Advanced Analytics</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["Real-Time", "History", "Ask Data"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    if st.button("Refresh now", use_container_width=True):
        st.rerun()

    auto_refresh = st.toggle("Auto-refresh (60s)", value=False)
    if auto_refresh:
        import time
        st.caption("Page will refresh every 60 seconds.")
        time.sleep(60)
        st.rerun()

    st.markdown("""
    <div style="position:absolute; bottom: 1.5rem; left: 0; right: 0; text-align:center;
                font-size: 0.7rem; color: #334155;">
        Powered by Google BigQuery<br>& OpenWeatherMap
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
