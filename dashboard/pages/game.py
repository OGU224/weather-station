import streamlit as st
import random
from pages.current import ALL_COMPANIONS, _companion

# Questions de culture générale (Vrai/Faux)
QUIZ_DATA = [
    ("Le soleil est une étoile.", True),
    ("Les requins sont des mammifères.", False),
    ("La capitale de l'Australie est Sydney.", False),
    ("L'eau bouillit à 90 degrés Celsius à l'altitude de la mer.", False),
    ("Une pieuvre possède trois cœurs.", True),
    ("Le mont Everest est la montagne la plus haute du monde.", True),
    ("Le chocolat noir est toxique pour les chiens.", True),
    ("Il y a 50 cartes dans un jeu de cartes standard.", False),
    ("Le Japon est composé de plus de 6 000 îles.", True),
    ("La Grande Muraille de Chine est visible depuis la Lune à l'œil nu.", False),
]

def render():
    st.markdown("""
    <div class="pixel-shell">
        <div class="hero-band">
            <div class="eyebrow">MONSTER GYM</div>
            <h1>Companion & Training</h1>
            <p>Switch your active companion and train them with ancient knowledge.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- SECTION 1 : CHOIX DU COMPAGNON ---
    st.markdown('<div class="pixel-title">SELECT ACTIVE COMPANION</div>', unsafe_allow_html=True)
    
    cols = st.columns(6)
    for i, (name, _) in enumerate(ALL_COMPANIONS):
        with cols[i]:
            is_selected = st.session_state["selected_companion_idx"] == i
            border = "4px solid #ffcc5c" if is_selected else "2px solid #2e3b47"
            
            # Affichage de la carte de sélection
            st.markdown(f"""
            <div style="background:#111; border:{border}; padding:10px; text-align:center;">
                {_companion(i, 40)}
                <div style="color:#888; font-size:0.6rem; margin-top:5px;">{name}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("CHOOSE", key=f"sel_{i}", use_container_width=True):
                st.session_state["selected_companion_idx"] = i
                st.rerun()

    st.markdown('<div style="height:30px;"></div>', unsafe_allow_html=True)

    # --- SECTION 2 : LE MINI-JEU (TRAINING) ---
    idx = st.session_state["selected_companion_idx"]
    name, _ = ALL_COMPANIONS[idx]
    stats = st.session_state["companion_stats"][name]

    st.markdown(f'<div class="pixel-title">TRAIN {name.upper()} (LV {stats["level"]})</div>', unsafe_allow_html=True)

    # Logique du Quiz
    if "current_q" not in st.session_state:
        st.session_state.current_q = random.choice(QUIZ_DATA)

    q_text, q_answer = st.session_state.current_q

    # Dialogue Box Undertale pour la question
    st.markdown(f"""
    <div style="background:#000; border:4px solid #fff; padding:25px; display:flex; gap:20px; align-items:center;">
        <div style="flex-shrink:0;">{_companion(idx, 64)}</div>
        <div style="flex:1;">
            <div style="color:#ffff00; font-family:monospace; font-weight:bold; font-size:0.8rem; margin-bottom:10px;">* {name.upper()} ASKS :</div>
            <div style="color:#ffffff; font-family:'Courier New', monospace; font-size:1.1rem; line-height:1.4;">
                "{q_text}"
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("TRUE", use_container_width=True):
            check_answer(True, q_answer, name)
    with c2:
        if st.button("FALSE", use_container_width=True):
            check_answer(False, q_answer, name)
    with c3:
        if st.button("NEXT QUESTION", use_container_width=True):
            st.session_state.current_q = random.choice(QUIZ_DATA)
            st.rerun()

def check_answer(user_val, correct_val, name):
    if user_val == correct_val:
        st.toast(f"CORRECT! {name} gained 1 XP!", icon="⭐")
        st.session_state["companion_stats"][name]["xp"] += 1
        
        # Passage de niveau tous les 5 XP
        new_level = (st.session_state["companion_stats"][name]["xp"] // 5) + 1
        if new_level > st.session_state["companion_stats"][name]["level"]:
            st.session_state["companion_stats"][name]["level"] = new_level
            st.balloons()
            st.success(f"LEVEL UP! {name} is now level {new_level}!")
    else:
        st.error("Incorrect... Try again!")
    
    # On change de question après une réponse
    st.session_state.current_q = random.choice(QUIZ_DATA)
    import time
    time.sleep(1)
    st.rerun()
