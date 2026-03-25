import streamlit as st
import streamlit.components.v1 as components

# --- KONFIGURACJA ---
st.set_page_config(page_title="MR Therapy", page_icon="🌿", layout="centered")

# --- LUKSUSOWY DESIGN (CSS) ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Lato:wght@300;400&display=swap');

    /* Kolory i Tło */
    .stApp {{
        background-color: #FDFBF7;
        color: #5C4D43;
    }}
    
    html, body, [data-testid="stSidebar"] {{
        font-family: 'Lato', sans-serif;
    }}

    h1, h2, h3, .serif-text {{
        font-family: 'Playfair Display', serif;
        color: #4B3F36;
    }}

    /* iOS Tab Bar (Bottom) */
    .nav-bar {{
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background: rgba(253, 251, 247, 0.8);
        backdrop-filter: blur(15px);
        display: flex;
        justify-content: space-around;
        padding: 15px 0;
        border-top: 1px solid rgba(212, 193, 179, 0.3);
        z-index: 1000;
    }}
    
    .nav-item {{
        text-align: center;
        color: #5C4D43;
        font-size: 10px;
        text-decoration: none;
    }}

    /* Karty Glassmorphism */
    .glass-card {{
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(212, 193, 179, 0.5);
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }}

    /* Wyzwanie 21 Dni - Siatka */
    .grid-container {{
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 10px;
        margin-top: 20px;
    }}
    .day-circle {{
        width: 35px;
        height: 35px;
        border-radius: 50%;
        border: 1px solid #D4C1B3;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        cursor: pointer;
    }}
    .day-done {{
        background-color: #D4C1B3;
        color: white;
    }}

    /* Ukrywanie standardowych elementów Streamlit */
    #MainMenu, footer, header {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE (Nawigacja) ---
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Pulpit"
if 'challenge_progress' not in st.session_state:
    st.session_state.challenge_progress = [False] * 21

# --- MENU NAWIGACJI (Customowe przyciski symulujące Tab Bar) ---
# Uwaga: Streamlit nie pozwala na łatwe przyciski w stałym footerze, 
# więc używamy st.columns jako górnego lub bocznego menu, ale stylizujemy je.

cols = st.columns(4)
with cols[0]:
    if st.button("🏠\nPulpit"): st.session_state.active_tab = "Pulpit"
with cols[1]:
    if st.button("📍\nDiagnoza"): st.session_state.active_tab = "Diagnoza"
with cols[2]:
    if st.button("📅\nWyzwanie"): st.session_state.active_tab = "Wyzwanie"
with cols[3]:
    if st.button("✨\nRytuał"): st.session_state.active_tab = "Rytuał"

st.markdown("---")

# --- LOGIKA EKRANÓW ---

if st.session_state.active_tab == "Pulpit":
    st.markdown("<h1 style='text-align: center;'>MR Therapy</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-style: italic;'>Zatrzymaj się. Poczyń przestrzeń dla siebie.</p>", unsafe_allow_html=True)
    
    st.image("https://images.unsplash.com/photo-1544161515-4ab6ce6db874?q=80&w=800&auto=format&fit=crop", use_container_width=True)
    
    with st.expander("🍃 Dźwięki relaksu (ASMR)"):
        st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3") # Przykładowy relaksacyjny loop
        st.caption("Włącz i poczuj spokój podczas przeglądania.")

    st.markdown("""
    <div class='glass-card'>
        <h3 class='serif-text'>Regulacja dla dzieci</h3>
        <p>Specjalistyczna pomoc w stanach przebodźcowania, tikach i problemach ze snem u najmłodszych.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Kontakt")
    st.info("📍 Przasnysz, ul. Ostrołęcka 28\n\n📍 Olsztyn, ul. Jagiellońska 44b/6")

elif st.session_state.active_tab == "Diagnoza":
    st.markdown("<h2 class='serif-text'>Interaktywna Mapa Twarzy</h2>", unsafe_allow_html=True)
    st.write("Kliknij w obszar, aby dowiedzieć się, co mówi Twoje ciało.")

    # Symulacja Mapy Twarzy za pomocą przycisków (Streamlit nie wspiera natywnie SVG click)
    diag_col1, diag_col2 = st.columns(2)
    
    with diag_col1:
        if st.button("Czoło: Centrum Kontroli"):
            st.warning("**Czoło:** Tu kumulujesz nadmierną kontrolę. Spięte mięśnie to sygnał stresu dla mózgu. Rekomendacja: Facemodeling.")
        if st.button("Żuchwa: Magazyn Stresu"):
            st.warning("**Żuchwa:** Tu zapisują się niewypowiedziane emocje (Bruksizm). Rekomendacja: Terapia Transbukalna.")
    
    with diag_col2:
        if st.button("Oczy: Lustro Zmęczenia"):
            st.warning("**Oczy:** Zastoje limfy to brak oddechu w ciele. Rekomendacja: Kobido i drenaż.")
        if st.button("Szyja: Fundament"):
            st.warning("**Szyja:** Skrócone powięzi ściągają owal w dół. Rekomendacja: Estetyczna Rehabilitacja.")

elif st.session_state.active_tab == "Wyzwanie":
    st.markdown("<h2 class='serif-text'>21 Dni Blasku</h2>", unsafe_allow_html=True)
    st.write("Twoja droga do naturalnego liftingu. Odhaczaj wykonany rytuał każdego dnia.")
    
    # Renderowanie siatki wyzwania
    cols_grid = st.columns(7)
    for i in range(21):
        with cols_grid[i % 7]:
            label = f"Dzień {i+1}"
            if st.session_state.challenge_progress[i]:
                if st.button("✅", key=f"day_{i}"):
                    st.session_state.challenge_progress[i] = False
                    st.rerun()
            else:
                if st.button(f"{i+1}", key=f"day_{i}"):
                    st.session_state.challenge_progress[i] = True
                    st.rerun()
    
    progress = sum(st.session_state.challenge_progress)
    st.progress(progress / 21)
    st.write(f"Ukończono {progress} z 21 dni. Jesteś cudowna!")

elif st.session_state.active_tab == "Rytuał":
    st.markdown("<h2 class='serif-text'>Codzienny Rytuał</h2>", unsafe_allow_html=True)
    
    # Tryb Lustra - Realizacja techniczna w Streamlit przez Camera Input
    show_mirror = st.toggle("✨ Włącz tryb lustra")
    if show_mirror:
        st.camera_input("Twoje lustro", label_visibility="collapsed")
        st.caption("Widzisz siebie? Teraz naśladuj ruchy Magdy.")

    st.markdown("### Wybierz masaż na dziś:")
    
    tab1, tab2, tab3 = st.tabs(["Head Spa", "Facemodeling", "Babuu"])
    
    with tab1:
        st.video("https://www.instagram.com/reel/DImUV4FNw_F/")
        st.markdown("[Poczuj rozluźnienie na Instagramie →](https://www.instagram.com/reel/DImUV4FNw_F/)")
    with tab2:
        st.video("https://www.instagram.com/reel/DI1Xfx7NfT7/")
    with tab3:
        st.video("https://www.instagram.com/reel/DIO8P4-tjrv/")

# --- FOOTER ---
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown("""
    <div style='text-align: center; color: #A98D80; font-size: 12px;'>
        MR Therapy | Magdalena Rykowska<br>
        Instagram: @mr__therapy_ | Facebook: MrtherapyMagdalenaRykowska
    </div>
""", unsafe_allow_html=True)
