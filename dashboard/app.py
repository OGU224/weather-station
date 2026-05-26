
#Streamlit dashboard entry point

import os
import sys

import streamlit as st

from pages.current import ALL_COMPANIONS, _companion

if "selected_companion_idx" not in st.session_state:
    st.session_state["selected_companion_idx"] = 0

st.set_page_config(
    page_title="Weather Home",
    page_icon="cloud",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700&display=swap');
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

.main, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #0b0f0e !important;
}

.block-container, [data-testid="stVerticalBlock"] {
    background: transparent !important;
}

header[data-testid="stHeader"] {
    background: #0b0f0e !important;
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

h1 {
    letter-spacing: 0;
    font-weight: 700;
    margin-bottom: 0.35rem;
    color: #f3f7f5;
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

/* --- LOGIQUE DE SURBRILLANCE POUR LA PAGE ACTIVE --- */
.stButton > button[data-testid="baseButton-primary"] {
    border-color: #ffcc5c !important;
    background: #2b2615 !important;
    color: #ffcc5c !important;
    box-shadow: 0 0 10px rgba(255, 204, 92, 0.3);
}

.stButton > button:focus {
    border-color: #39d0ff;
    box-shadow: none;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-baseweb="select"] > div {
    background: #11171b;
    border: 2px solid #2e3b47;
    border-radius: 0;
    color: #f3f7f5;
}
</style>
""", unsafe_allow_html=True)

if "dashboard_page" not in st.session_state:
    st.session_state["dashboard_page"] = "Smart Home"

with st.sidebar:
    idx = st.session_state["selected_companion_idx"]
    name, _ = ALL_COMPANIONS[idx]
    
    st.markdown(f"""
    <div class="sidebar-brand" style="text-align:center;">
        <div style="color:#ffcc5c; font-family:'Press Start 2P'; font-size:0.6rem; margin-bottom:10px;">
            WEATHER PARTY
        </div>
        <div style="margin-bottom:15px;">
            {_companion(idx, 80)}
        </div>
        <div class="sidebar-brand-title">{name.upper()}</div>
        <div class="sidebar-brand-subtitle">Cloud companion online</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="pixel-menu-label">SELECT MODE</div>', unsafe_allow_html=True)

    menu_items = [
        ("Smart Home", "Home Base"),
        ("Live Station", "Live Map"),
        ("History", "Data Archive"),
        ("Ask Data", "AI Console"),
    ]
    
    # Rendu dynamique avec gestion de la surbrillance
    for page_key, label in menu_items:
        is_active = st.session_state["dashboard_page"] == page_key
        prefix = "❤️ " if is_active else "  "
        btn_type = "primary" if is_active else "secondary"
        
        if st.button(prefix + label, use_container_width=True, key=f"nav_{page_key}", type=btn_type):
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

sys.path.insert(0, os.path.dirname(__file__))
page = st.session_state["dashboard_page"]

if page == "Smart Home":
    from pages.smart_home import render
elif page == "Live Station":
    from pages.current import render
elif page == "History":
    from pages.history import render
elif page == "Ask Data":
    from pages.ask import render
else:
    from pages.smart_home import render

render()
