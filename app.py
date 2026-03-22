import streamlit as st
import datetime
import math

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia", page_icon="🥛", layout="wide")

# CSS dla wyglądu raportu
st.markdown("""
    <style>
    .day-card { border: 2px solid #e6e9ef; border-radius: 10px; padding: 10px; background-color: #ffffff; margin-bottom: 10px; min-height: 150px; }
    .day-header { background-color: #ffe600; font-weight: bold; text-align: center; padding: 5px; border-radius: 5px; margin-bottom: 10px; color: black; }
    .art-row { display: flex; justify-content: space-between; border-bottom: 1px solid #f0f0f0; padding: 3px 0; font-size: 0.9em; }
    .deadline-ok { color: green; font-size: 0.8em; font-weight: bold; }
    .deadline-late { color: white; background-color: red; padding: 2px; border-radius: 3px; font-size: 0.8em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🥛 Harmonogram Produkcji")

# Inicjalizacja listy w sesji
if 'lista' not in st.session_state:
    st.session_state.lista = []

# PANEL BOCZNY
with st.sidebar:
    st.header("➕ Nowe zamówienie")
    with st.form("dodaj_form"):
        wybrany_art = st.selectbox("Artykuł:", list(wydajnosc.keys()))
        ile_palet = st.number_input("Ilość palet:", min_value=1, step=1)
        data_deadline = st.date_input("Termin:", datetime.date.today() + datetime.timedelta(days=2))
        klik = st.form_submit_button("Dodaj do listy")
        
        if klik:
            st.session_state.lista.append({
                "art": wybrany_art,
                "ile": ile_palet,
                "deadline": data_deadline
            })

    if st.button("🗑️ Wyczyść wszystko"):
        st.session_state.lista = []
        st.rerun()

    st.write("---")
    st.write("**Aktualna lista:**")
    for z in st.session_state.lista:
        st.write(f"• {z['art']}: {z['ile']} pal. (do {z['deadline'].strftime('%d.%m')})")

# GŁÓWNA SEKCJA
if st.session_state.lista:
    if st.button("🚀 GENERUJ HARMONOGRAM", type="primary", use_container_width=True):
        dni_planu = {}
        czas_dniowki = 840  # 14h
        aktualna_data = datetime.date.today()
        wolny_czas = czas_dni
