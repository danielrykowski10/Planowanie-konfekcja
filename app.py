import streamlit as st
import datetime
import math

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia v3", page_icon="🥛", layout="wide")

# CSS dla wyglądu
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

# Inicjalizacja listy zamówień w pamięci przeglądarki
if 'lista_zamowien' not in st.session_state:
    st.session_state.lista_zamowien = []

# PANEL BOCZNY
with st.sidebar:
    st.header("➕ Dodaj nowe zamówienie")
    with st.form("form_dodawania", clear_on_submit=True):
        art = st.selectbox("Artykuł:", list(wydajnosc.keys()))
        ile = st.number_input("Ilość palet:", min_value=1, step=1)
        termin = st.date_input("Termin (do kiedy):", datetime.date.today() + datetime.timedelta(days=2))
        submit_button = st.form_submit_button("Dodaj do listy")
        
        if submit_button:
            st.session_state.lista_zamowien.append({
                "art": art,
                "ile": ile,
                "termin": termin
            })

    if st.button("🗑️ Wyczyść wszystko"):
        st.session_state.lista_zamowien = []
        st.rerun()

    st.write("---")
    st.write("**Twoja lista:**")
    for i, z in enumerate(st.session_state.lista
