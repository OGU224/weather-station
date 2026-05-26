import os
import requests
import streamlit as st
from html import escape
from pages.current import _companion, ALL_COMPANIONS

MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "https://weather-middleware-387666611940.europe-west1.run.app")

SUGGESTED_QUESTIONS = [
    "Summarize the latest indoor conditions.",
    "What was the average temperature over the last 24h?",
    "How many times was motion detected?",
    "Should I ventilate the room?",
    "Was air quality poor recently?",
]

def _ask(question: str, device_id: str, hours: int):
    response = requests.post(
        f"{MIDDLEWARE_URL}/api/voice/ask",
        json={"question": question, "device_id": device_id or None, "hours": hours},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def _tts(text: str):
    response = requests.post(
        f"{MIDDLEWARE_URL}/api/voice/tts",
        json={"text": text},
        timeout=45,
    )
    response.raise_for_status()
    return (
        response.content,
        response.headers.get("X-TTS-Provider", "tts"),
        response.headers.get("Content-Type", "audio/mpeg").split(";")[0],
    )

def _stt(audio_file, language_code: str):
    files = {"audio": (getattr(audio_file, "name", "question.wav"), audio_file.getvalue(), getattr(audio_file, "type", "audio/wav"))}
    data = {"language_code": language_code}
    response = requests.post(f"{MIDDLEWARE_URL}/api/voice/stt", files=files, data=data, timeout=45)
    response.raise_for_status()
    return response.json()

def render():
    st.markdown("""
    <div class="pixel-shell">
        <div class="hero-band">
            <div class="eyebrow">SYSTEM TERMINAL</div>
            <h1>AI Console</h1>
            <p>Direct neural link to home sensors. Query the database via natural language.</p>
            <div class="mission-row">
                <span class="mission-chip">LEVEL 20</span>
                <span class="mission-chip">HP 99/99</span>
                <span class="mission-chip">ATK 45</span>
                <span class="mission-chip">DF 30</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:25px;"></div>', unsafe_allow_html=True)

    # Valeurs par défaut fixées en tâche de fond (Pas d'affichage de configuration métallique)
    device_id = None
    hours = 24

    col_left, col_right = st.columns([2, 1])

    with col_left:
        # Dialogue Box Undertale permanente guidant l'utilisateur
        st.markdown(f"""
        <div style="background:#000; border:3px solid #fff; padding:15px; display:flex; gap:15px; align-items:center; height:100px;">
            <div style="flex-shrink:0;">{_companion(0, 48)}</div>
            <div style="color:#fff; font-family:'Courier New', monospace; font-size:0.9rem;">
                * System is online.<br>
                * Select an action from the combat menu or write down a custom query.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown(f"""
        <div style="background:#050505; border:3px solid #2e3b47; text-align:center; padding:10px; border-radius:4px; height:100px; display:flex; flex-direction:column; justify-content:center; align-items:center;">
            {_companion(4, 52)}
            <div style="color:#888; font-family:monospace; font-size:0.6rem; margin-top:4px; letter-spacing:2px;">ASSISTANT_ACTIVE</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)

    st.markdown('<div class="pixel-title">⚔️ ACTIONS MENU</div>', unsafe_allow_html=True)
    
    cols = st.columns(3)
    for i, suggested in enumerate(SUGGESTED_QUESTIONS):
        with cols[i % 3]:
            if st.button(f"❤️ {suggested}", use_container_width=True, key=f"preset_{i}"):
                st.session_state["ask_question"] = suggested

    st.markdown('<div style="height:25px;"></div>', unsafe_allow_html=True)

    st.markdown('<div class="pixel-title">⌨️ INPUT BUFFER</div>', unsafe_allow_html=True)
    
    question = st.text_area(
        "Custom Query",
        key="ask_question",
        height=85,
        placeholder="TYPE YOUR COMMAND OR CLICK AN ACTION...",
        label_visibility="collapsed"
    )

    b1, b2, b3 = st.columns([2, 2, 1])
    with b1:
        ask_clicked = st.button("🌟 EXECUTE COMMAND", type="primary", use_container_width=True)
    with b2:
        with st.popover("🎤 VOCAL INPUT", use_container_width=True):
            lang = st.radio("Language Proxy", ["en-US", "fr-FR"], horizontal=True)
            audio = st.audio_input("Microphone Interface")
            if audio:
                if st.button("TRANSCRIBE STREAM"):
                    with st.spinner("Decoding waveforms..."):
                        res = _stt(audio, lang)
                        st.session_state["ask_question"] = res.get("transcript", "")
                        st.rerun()
    with b3:
        if st.button("RESET", use_container_width=True):
            st.session_state.pop("last_answer_result", None)
            st.rerun()

    if ask_clicked and question:
        with st.spinner("PARSING SENSOR DATA..."):
            try:
                res = _ask(question, device_id, hours)
                st.session_state["last_answer_result"] = res
            except Exception as e:
                st.error(f"Link severed: {e}")

    result = st.session_state.get("last_answer_result")
    if result:
        st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="pixel-title">💬 DIALOGUE RESPONSE</div>', unsafe_allow_html=True)
        
        answer = result.get("answer", "...")
        
        st.markdown(f"""
        <div style="background:#000; border:4px solid #fff; padding:25px; display:flex; gap:20px; align-items:flex-start; margin-bottom:15px;">
            <div style="flex-shrink:0; padding-top:5px;">{_companion(1, 64)}</div>
            <div style="flex:1;">
                <div style="color:#ffff00; font-family:monospace; font-weight:bold; font-size:0.8rem; margin-bottom:12px; letter-spacing:1px;">* ANALYSIS COMPLETE :</div>
                <div style="color:#ffffff; font-family:'Courier New', monospace; font-size:1.1rem; line-height:1.6;">
                    {answer}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        audio_col, padding_col = st.columns([1.5, 3.5])
        with audio_col:
            if st.button("🔊 READ TEXT ALOUD", use_container_width=True):
                with st.spinner("Synthesizing speech..."):
                    audio_bytes, _, _ = _tts(answer)
                    st.audio(audio_bytes, format="audio/mpeg")
        with padding_col:
            source = result.get("source", "BigQuery")
            st.markdown(f"""<div style="color:#555; font-size:0.75rem; text-align:right; font-family:monospace; margin-top:12px;">DATABASE_SOURCE: {source}</div>""", unsafe_allow_html=True)