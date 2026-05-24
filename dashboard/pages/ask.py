import os

import requests
import streamlit as st

MIDDLEWARE_URL = os.getenv("MIDDLEWARE_URL", "http://127.0.0.1:5000")

SUGGESTED_QUESTIONS = [
    "Summarize the latest indoor conditions.",
    "Summarize yesterday.",
    "What was the average temperature over the last 24 hours?",
    "How many times was motion detected?",
    "Was humidity too low recently?",
    "How was the air quality over the last day?",
    "Should I ventilate the room?",
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
    if response.status_code >= 400:
        try:
            detail = response.json().get("error", response.text)
        except ValueError:
            detail = response.text
        raise requests.HTTPError(detail or f"TTS failed with status {response.status_code}")
    return (
        response.content,
        response.headers.get("X-TTS-Provider", "tts"),
        response.headers.get("Content-Type", "audio/mpeg").split(";")[0],
    )


def _stt(audio_file, language_code: str):
    files = {
        "audio": (
            getattr(audio_file, "name", "question.wav"),
            audio_file.getvalue(),
            getattr(audio_file, "type", "audio/wav"),
        )
    }
    data = {"language_code": language_code}
    response = requests.post(
        f"{MIDDLEWARE_URL}/api/voice/stt",
        files=files,
        data=data,
        timeout=45,
    )
    if response.status_code >= 400:
        try:
            detail = response.json().get("error", response.text)
        except ValueError:
            detail = response.text
        raise requests.HTTPError(detail or f"STT failed with status {response.status_code}")
    return response.json()


def render():
    st.markdown("""
    <div class="pixel-shell">
        <div class="hero-band">
            <div class="eyebrow">AI CONSOLE</div>
            <h1>Ask The Station</h1>
            <p>Ask about comfort, weather, motion, and recent room trends.</p>
            <div class="mission-row">
                <span class="mission-chip">Smart answers</span>
                <span class="mission-chip">Voice input</span>
                <span class="mission-chip">Spoken reply</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        device_id = st.text_input("Room filter", value="", placeholder="Whole home")
    with col2:
        hours = st.selectbox("Time gate", [1, 2, 6, 12, 24, 48, 168], index=4)

    if "ask_question" not in st.session_state:
        st.session_state["ask_question"] = SUGGESTED_QUESTIONS[0]

    with st.expander("Command presets", expanded=True):
        cols = st.columns(2)
        for index, suggested in enumerate(SUGGESTED_QUESTIONS):
            with cols[index % 2]:
                if st.button(suggested, use_container_width=True):
                    st.session_state["ask_question"] = suggested

    with st.expander("Voice command", expanded=False):
        language_code = st.selectbox("Speech language", ["en-US", "fr-FR"], index=0)
        audio_input = None
        if hasattr(st, "audio_input"):
            audio_input = st.audio_input("Record command")
        else:
            st.info("Your Streamlit version does not support browser audio recording. Update Streamlit to use this.")

        if audio_input and st.button("Decode voice", use_container_width=True):
            with st.spinner("Listening..."):
                try:
                    transcript = _stt(audio_input, language_code=language_code)
                except requests.RequestException as exc:
                    st.error(f"Could not transcribe audio: {exc}")
                else:
                    text = transcript.get("transcript", "").strip()
                    if text:
                        st.session_state["ask_question"] = text
                        st.success("Voice question added below.")
                        st.rerun()
                    else:
                        st.warning("No speech was detected in the recording.")

    question = st.text_area(
        "Command line",
        key="ask_question",
        height=100,
        placeholder="Ask something like: What was the average humidity today?",
    )

    ask_col, clear_col = st.columns([3, 1])
    with ask_col:
        ask_clicked = st.button("Run query", type="primary", use_container_width=True)
    with clear_col:
        if st.button("Reset", use_container_width=True):
            st.session_state.pop("last_answer_result", None)
            st.session_state.pop("last_answer_audio", None)
            st.rerun()

    if ask_clicked:
        if not question.strip():
            st.warning("Write a question first.")
        else:
            with st.spinner("Thinking..."):
                try:
                    result = _ask(question=question, device_id=device_id, hours=hours)
                except requests.RequestException as exc:
                    st.error("The assistant is unavailable right now.")
                    return
            st.session_state["last_answer_result"] = result
            st.session_state.pop("last_answer_audio", None)
            st.session_state.pop("last_answer_audio_provider", None)

    result = st.session_state.get("last_answer_result")
    if result:
        st.markdown('<div class="pixel-title">ASSISTANT OUTPUT</div>', unsafe_allow_html=True)
        answer = result.get("answer", "No answer returned.")
        st.markdown(f"""
        <div class="console-panel">{answer}</div>
        """, unsafe_allow_html=True)

        source = result.get("source", "unknown")
        if source in {"local-fallback", "local-fallback-after-error"}:
            st.info("Answer prepared from recent station readings.")

        speak_col, _ = st.columns([1.2, 2.8])
        with speak_col:
            if st.button("Speak", use_container_width=True):
                with st.spinner("Preparing voice..."):
                    try:
                        audio, provider, content_type = _tts(answer)
                    except requests.RequestException as exc:
                        st.error("Voice playback is unavailable right now.")
                    else:
                        st.session_state["last_answer_audio"] = audio
                        st.session_state["last_answer_audio_provider"] = provider
                        st.session_state["last_answer_audio_type"] = content_type

        audio = st.session_state.get("last_answer_audio")
        if audio:
            st.audio(audio, format=st.session_state.get("last_answer_audio_type", "audio/mpeg"))
