"""
Streamlit dashboard entry point.
"""

import os
import sys

import streamlit as st

st.set_page_config(
    page_title="Weather Home",
    page_icon="cloud",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

div[data-testid="stSidebarNav"] {
    display: none;
}

section[data-testid="stSidebar"] {
    background:
        linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px),
        #101316;
    background-size: 16px 16px;
    border-right: 3px solid #2e3b47;
}

section[data-testid="stSidebar"] > div {
    padding-top: 0.75rem;
}

[data-testid="stSidebarUserContent"] {
    padding: 1rem 1.25rem 1.25rem 1.25rem;
}

.main {
    background: #0b0f0e;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1360px;
}

[data-testid="metric-container"] {
    background: #171d1b;
    border-radius: 0;
    padding: 12px 16px;
    border: 3px solid #2e3b47;
}

.pixel-shell {
    background:
        linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px),
        #0d1114;
    background-size: 18px 18px;
    border: 3px solid #2e3b47;
    box-shadow: 0 0 0 3px #070a0c, 0 12px 0 #070a0c;
    border-radius: 0;
    padding: 18px;
    margin-bottom: 18px;
}

.hero-band {
    background: linear-gradient(135deg, #13252a 0%, #121719 52%, #2c2410 100%);
    border: 3px solid #2e3b47;
    border-radius: 0;
    padding: 16px 18px;
    margin-bottom: 14px;
    position: relative;
    overflow: hidden;
}

.hero-band h1 {
    margin: 0;
    color: #f3f7f5;
    font-size: 1.7rem;
    line-height: 1.1;
}

.hero-band p {
    margin: 0.45rem 0 0 0;
    color: #aab7b2;
    font-size: 0.88rem;
}

.eyebrow {
    color: #ffcc5c;
    font-family: 'Press Start 2P', monospace;
    font-size: 0.52rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.45rem;
}

.section-title {
    color: #f3f7f5;
    font-size: 1.02rem;
    font-weight: 750;
    margin: 0.65rem 0 0.55rem 0;
}

.pixel-title {
    font-family: 'Press Start 2P', monospace;
    color: #f3f7f5;
    font-size: 0.72rem;
    line-height: 1.8;
    margin: 0.4rem 0 0.55rem 0;
}

.dash-card {
    background: #151b1f;
    border: 3px solid #2e3b47;
    border-radius: 0;
    padding: 14px 15px;
    min-height: 106px;
    margin-bottom: 10px;
}

.dash-card.compact {
    min-height: 92px;
}

.dash-label {
    color: #82908b;
    font-size: 0.64rem;
    font-weight: 750;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.35rem;
}

.dash-value {
    color: #f3f7f5;
    font-size: 1.35rem;
    line-height: 1.12;
    font-weight: 760;
    overflow-wrap: anywhere;
}

.dash-detail {
    color: #aab7b2;
    font-size: 0.86rem;
    line-height: 1.35;
    margin-top: 0.45rem;
}

.routine-panel {
    background: #11171b;
    border: 3px solid #2e3b47;
    border-radius: 0;
    padding: 16px 17px;
    min-height: 166px;
}

.routine-text {
    color: #f3f7f5;
    font-size: 1.1rem;
    line-height: 1.45;
    font-weight: 650;
}

.routine-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
    margin-top: 16px;
}

.routine-grid span {
    background: #0f1412;
    border: 2px solid #2e3b47;
    border-radius: 0;
    color: #aab7b2;
    padding: 7px 9px;
    font-size: 0.78rem;
}

.smart-panel, .smart-panel-soft {
    background: #151a19;
    border: 1px solid #2d3436;
    border-radius: 8px;
    padding: 16px 18px;
}

.pixel-avatar {
    width: 86px;
    height: 86px;
    margin: 0 auto 0.9rem auto;
    background:
      linear-gradient(#0000 0 0),
      #39d0ff;
    image-rendering: pixelated;
    box-shadow:
      0 0 0 8px #111316,
      8px 0 0 8px #111316,
      -8px 0 0 8px #111316,
      0 8px 0 8px #111316,
      0 -8px 0 8px #111316,
      16px 16px 0 0 #ffcc5c,
      -16px 16px 0 0 #ffcc5c;
    position: relative;
}

.pixel-avatar::before {
    content: "";
    position: absolute;
    left: 18px;
    top: 26px;
    width: 10px;
    height: 10px;
    background: #071014;
    box-shadow: 40px 0 0 #071014, 20px 28px 0 8px #071014;
}

.pixel-avatar::after {
    content: "";
    position: absolute;
    left: 28px;
    top: -20px;
    width: 30px;
    height: 12px;
    background: #ffcc5c;
    box-shadow: 0 -10px 0 #ffcc5c;
}

.pixel-menu-label {
    color: #76848e;
    font-family: 'Press Start 2P', monospace;
    font-size: 0.52rem;
    line-height: 1.8;
    margin: 0.9rem 0 0.45rem 0;
}

.sidebar-status {
    border: 3px solid #2e3b47;
    background: #151b1f;
    padding: 10px;
    color: #aab7b2;
    font-size: 0.78rem;
    line-height: 1.4;
}

.smart-label {
    color: #82908b;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.35rem;
}

.smart-value {
    color: #f3f7f5;
    font-size: 2.1rem;
    line-height: 1;
    font-weight: 750;
}

.smart-copy {
    color: #aab7b2;
    font-size: 0.94rem;
    line-height: 1.45;
}

.smart-pill {
    display: inline-block;
    border: 1px solid #2d3436;
    background: #0f1412;
    color: #aab7b2;
    border-radius: 6px;
    padding: 0.24rem 0.58rem;
    margin: 0.12rem 0.18rem 0.12rem 0;
    font-size: 0.78rem;
}

h1 {
    letter-spacing: 0;
    font-weight: 700;
    margin-bottom: 0.35rem;
    color: #f3f7f5;
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
    background: #171d1b;
    border-color: #2d3436;
}

.sidebar-brand {
    padding: 0.75rem 0 1rem 0;
}

.sidebar-brand-title {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.78rem;
    font-weight: 700;
    color: #f3f7f5;
    line-height: 1.2;
}

.sidebar-brand-subtitle {
    font-size: 0.76rem;
    color: #9aa6a1;
    margin-top: 0.25rem;
}

.sidebar-section-label {
    color: #6f7c78;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 1rem 0 0.35rem 0;
}

.sidebar-footer {
    color: #6f7c78;
    font-size: 0.72rem;
    line-height: 1.35;
    padding-top: 1rem;
}

.stButton > button {
    border-radius: 0;
    border: 3px solid #2e3b47;
    background: #151b1f;
    color: #f3f7f5;
    min-height: 44px;
    font-weight: 760;
}

.stButton > button:hover {
    border-color: #ffcc5c;
    background: #1e2b31;
    color: #f3f7f5;
}

.stButton > button:focus {
    border-color: #39d0ff;
    box-shadow: none;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 3px solid #2e3b47;
}

.stTabs [data-baseweb="tab"] {
    background: #151b1f;
    border: 3px solid #2e3b47;
    border-bottom: 0;
    border-radius: 0;
    color: #aab7b2;
    font-weight: 760;
    padding: 9px 14px;
}

.stTabs [aria-selected="true"] {
    background: #1e2b31;
    color: #f3f7f5;
}

div[data-testid="stExpander"] {
    background: #11171b;
    border: 3px solid #2e3b47;
    border-radius: 0;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-baseweb="select"] > div {
    background: #11171b;
    border: 2px solid #2e3b47;
    border-radius: 0;
    color: #f3f7f5;
}

.console-panel {
    background: #071014;
    border: 3px solid #2e3b47;
    box-shadow: inset 0 0 0 2px #11171b;
    border-radius: 0;
    padding: 16px;
    color: #d9f8f0;
    font-family: 'Inter', sans-serif;
    line-height: 1.55;
}

.mission-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 10px;
}

.mission-chip {
    background: #0f1412;
    border: 2px solid #2e3b47;
    color: #aab7b2;
    padding: 6px 9px;
    font-size: 0.78rem;
}
</style>
""", unsafe_allow_html=True)

if "dashboard_page" not in st.session_state:
    st.session_state["dashboard_page"] = "Smart Home"

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="pixel-avatar"></div>
        <div class="sidebar-brand-title">WEATHER HOME</div>
        <div class="sidebar-brand-subtitle">Smart morning companion</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="pixel-menu-label">SELECT MODE</div>', unsafe_allow_html=True)

    menu_items = [
        ("Smart Home", "Home Base"),
        ("Live Station", "Live Map"),
        ("History", "Data Archive"),
        ("Ask Data", "AI Console"),
    ]
    for page_key, label in menu_items:
        prefix = "> " if st.session_state["dashboard_page"] == page_key else ". "
        if st.button(prefix + label, use_container_width=True, key=f"nav_{page_key}"):
            st.session_state["dashboard_page"] = page_key
            st.rerun()

    st.markdown('<div class="pixel-menu-label">SYSTEM</div>', unsafe_allow_html=True)

    if st.button("Refresh now", use_container_width=True):
        st.rerun()

    auto_refresh = st.toggle("Auto-refresh (60s)", value=False)
    if auto_refresh:
        import time
        st.caption("Page will refresh every 60 seconds.")
        time.sleep(60)
        st.rerun()

    st.markdown("""
    <div class="sidebar-status">
        Live room comfort<br>
        Outdoor forecast<br>
        Voice assistant<br>
        Morning music
    </div>
    """, unsafe_allow_html=True)

sys.path.insert(0, os.path.dirname(__file__))

page = st.session_state["dashboard_page"]

if page == "Smart Home":
    from pages.smart_home import render
elif page == "Live Station":
    from pages.current import render
elif page == "History":
    from pages.history import render
else:
    from pages.ask import render

render()
