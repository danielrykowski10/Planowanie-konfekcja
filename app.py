import streamlit as st
import datetime
import pandas as pd

# Baza wydajności (minuty na 1 paletę)
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Produkcji", layout="wide")
st.title("🥛 Harmonogram Produkcji z Terminarzem")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- PANEL BOCZNY: FORMULARZ ---
with st.sidebar:
    st.header("📋 Nowe Zamówienie")
    with st.form("form_zbiorczy"):
        dane_wejsciowe = []
        for art_id in wydajnosc.keys():
            c1, c2 = st.columns([1, 1.5])
            with c1:
                ile = st.number_input(f"Art {art_id}", min_value=0, step=1, value=0, key=f"n_{art_id}")
            with c2:
                termin = st.date_input(f"Termin", datetime.date.today() + datetime.timedelta(days=3), key=f"t_{art_id}")
            
            if ile > 0:
                dane_wejsciowe.append({"art": art_id, "ile": ile, "termin": termin})
        
        st.write("---")
        data_startu = st.date_input("Od kiedy zacząć produkcję?", datetime.date.today())
        submit = st.form_submit_button("✅ DODAJ DO PLANU")
        
        if submit and dane_wejsciowe:
            for poz in dane_wejsciowe:
                st.session_state.kolejka.append({
                    "art": poz["art"], "ile": poz["ile"], 
                    "start": data_startu, "termin": poz["termin"]
                })
            st.rerun()

    if st.button("🗑️ WYCZYŚĆ PLAN"):
        st.session_state.kolejka = []
        st.rerun()

# --- LOGIKA PLANOWANIA ---
if not st.session_state.kolejka:
    st.info("👈 Wpisz ilości palet i daty dostaw w panelu bocznym.")
else:
    zad
