import streamlit as st

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="HMI - Zbiornik", layout="wide")

# --- STYLE CSS (Magia wyglądu SCADA) ---
st.markdown("""
    <style>
        /* Czcionki i kolory nagłówków */
        .scada-title {
            color: #61A854;
            font-family: 'Times New Roman', Times, serif;
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 30px;
        }
        
        /* Styl dla wierszy z danymi (Tekst po lewej, wartość po prawej) */
        .data-row {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            padding-right: 20px;
        }
        .data-label {
            margin-right: 15px;
        }
        .data-value {
            min-width: 80px;
            text-align: left;
        }

        /* --- KONTROLKI (LAMPKI) --- */
        .indicator-container {
            display: flex;
            align-items: center;
            margin-bottom: 25px;
            justify-content: center;
        }
        .lamp {
            width: 45px;
            height: 45px;
            border-radius: 50%;
            margin-right: 15px;
            box-shadow: inset -5px -5px 10px rgba(0,0,0,0.2);
        }
        .lamp-gray {
            background-color: #d9d9d9;
            border: 2px solid #ccc;
        }
        .lamp-green {
            background-color: #2ed11f;
            border: 2px solid #1fa113;
            box-shadow: 0 0 15px #2ed11f, inset -5px -5px 10px rgba(0,0,0,0.2);
        }
        .lamp-label {
            font-weight: bold;
            font-size: 14px;
        }

        /* --- ZBIORNIK 3D --- */
        .tank-wrapper {
            display: flex;
            justify-content: center;
            align-items: flex-end;
            height: 350px;
            margin-top: 20px;
        }
        .tank {
            width: 180px;
            height: 300px;
            background: linear-gradient(to right, #666 0%, #aaa 50%, #555 100%);
            border-radius: 15px / 10px; /* Tworzy efekt walca */
            position: relative;
            overflow: hidden;
            box-shadow: 5px 5px 15px rgba(0,0,0,0.3);
            border-top: 2px solid #999;
            border-bottom: 2px solid #333;
        }
        .tank-fill {
            position: absolute;
            bottom: 0;
            width: 100%;
            height: 50%; /* POZIOM WYPEŁNIENIA ZBIORNIKA */
            background: linear-gradient(to right, #007bff 0%, #66b3ff 50%, #0066cc 100%);
            border-top: 2px solid #005ce6;
        }
    </style>
""", unsafe_allow_html=True)


# --- GŁÓWNY UKŁAD STRONY ---

# Pasek górny (Logo i logowanie)
col_logo, col_empty, col_login = st.columns([2, 5, 2])
with col_logo:
    st.markdown("**🌐 BAJER ENTERPRISE**<br><small>INDUSTRIAL AUTOMATION</small>", unsafe_allow_html=True)
with col_login:
    # Atrapa pola logowania
    st.text_input("Hasło", type="password", label_visibility="collapsed", placeholder="hasło")
    c_btn1, c_btn2 = st.columns(2)
    c_btn1.button("Zaloguj", use_container_width=True)
    c_btn2.button("Wyloguj", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# Podział na 3 główne sekcje robocze (Lewa: Pomiary, Środek: Zbiornik, Prawa: Sterowanie)
col_left, col_center, col_right = st.columns([1.5, 1, 1.5])

# ==========================================
# LEWA KOLUMNA: WSKAŹNIKI I POMIARY
# ==========================================
with col_left:
    st.markdown("<div class='scada-title'>ZBIORNIK ZE ŚCIEKAMI</div>", unsafe_allow_html=True)
    
    # Dane ze zdjęcia wpisane na sztywno za pomocą HTML
    st.markdown("""
        <div class='data-row'><div class='data-label'>Zbiornik:</div><div class='data-value'>7.05 pH</div></div>
        <div class='data-row'><div class='data-label'>Przepływ:</div><div class='data-value'>5.98 pH</div></div>
        <br>
        <div class='data-row'><div class='data-label'>Przepływ chwilowy:</div><div class='data-value'>0 m3/h</div></div>
        <div class='data-row'><div class='data-label'>Przepływ od 8:00:</div><div class='data-value'>99.02 m3</div></div>
        <div class='data-row'><div class='data-label'>Przepływ poprzedni dzień:</div><div class='data-value'>799.63 m3</div></div>
        <br>
        <div class='data-row'><div class='data-label'>Dotąd pobrano:</div><div class='data-value'>15.08 m3</div></div>
    """, unsafe_allow_html=True)
    
    # Pole do wpisywania i przycisk (złożone w jednym wierszu)
    st.markdown("<br>", unsafe_allow_html=True)
    c_in1, c_in2 = st.columns([2, 1])
    with c_in1:
        st.markdown("<div style='text-align: right; font-weight: bold; font-size: 18px; margin-top: 5px;'>Ustawienie częstotliwości próby:</div>", unsafe_allow_html=True)
    with c_in2:
        nowa_proba = st.text_input("proba", label_visibility="collapsed")
        st.button("Zaakceptuj", key="btn_proba")
        
    st.markdown("<div class='data-row'><div class='data-label'>Częstotliwość próby:</div><div class='data-value'>18 m3</div></div>", unsafe_allow_html=True)

# ==========================================
# ŚRODKOWA KOLUMNA: POZIOMY I ZBIORNIK
# ==========================================
with col_center:
    c_lampki, c_zbiornik = st.columns([1, 2])
    
    with c_lampki:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # 4 poziomy (2 szare, 2 zielone)
        st.markdown("""
            <div class='indicator-container' style='flex-direction: column;'>
                <div class='lamp lamp-gray'></div><div class='lamp-label'>Poziom 4</div><br>
                <div class='lamp lamp-gray'></div><div class='lamp-label'>Poziom 3</div><br>
                <div class='lamp lamp-green'></div><div class='lamp-label'>Poziom 2</div><br>
                <div class='lamp lamp-green'></div><div class='lamp-label'>Poziom 1</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c_zbiornik:
        # Kod HTML/CSS renderujący zbiornik w 3D
        st.markdown("""
            <div class='tank-wrapper'>
                <div class='tank'>
                    <div class='tank-fill'></div>
                </div>
            </div>
        """, unsafe_allow_html=True)


# ==========================================
# PRAWA KOLUMNA: ZASUWY I STEROWANIE
# ==========================================
with col_right:
    st.markdown("<br><br>", unsafe_allow_html=True) # Wyrównanie w dół
    st.markdown("<div class='scada-title'>REGULACJA ZASUWY</div>", unsafe_allow_html=True)
    
    c_in3, c_in4, c_in5 = st.columns([1.5, 1, 1])
    with c_in3:
        st.markdown("<div style='text-align: right; font-weight: bold; font-size: 18px; margin-top: 5px;'>Zadaj przepływ:</div>", unsafe_allow_html=True)
    with c_in4:
        nowy_przeplyw = st.text_input("przeplyw", label_visibility="collapsed")
    with c_in5:
        st.button("Zaakceptuj", key="btn_przeplyw")
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='data-row' style='justify-content: center;'><div class='data-label'>Przepływ zadany:</div><div class='data-value'>80 m3</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    c_zas1, c_zas2 = st.columns(2)
    with c_zas1:
        st.markdown("""
            <div class='indicator-container' style='flex-direction: column;'>
                <div class='lamp lamp-gray'></div><div class='lamp-label'>Zasuwa max<br>otwarta</div>
            </div>
        """, unsafe_allow_html=True)
    with c_zas2:
         st.markdown("""
            <div class='indicator-container' style='flex-direction: column;'>
                <div class='lamp lamp-green'></div><div class='lamp-label'>Zasuwa max<br>zamknieta</div>
            </div>
        """, unsafe_allow_html=True)
