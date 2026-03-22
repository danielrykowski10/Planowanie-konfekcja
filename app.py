import streamlit as st
import datetime
import pandas as pd

# 1. Baza wydajności (minuty na 1 paletę)
WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Szybki Planista", layout="wide")
st.title("🥛 Harmonogram Produkcji (Wersja Turbo)")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("📋 Wprowadzanie")
    with st.form("form_szybki", clear_on_submit=True):
        cols_input = st.columns(2)
        dane_form = []
        for i, (art_id, czas) in enumerate(WYDAJNOSC.items()):
            # Wyświetlamy artykuły w dwóch kolumnach w menu dla szybkości
            with cols_input[i % 2]:
                n = st.number_input(f"Art {art_id}", min_value=0, step=1, value=0)
                if n > 0:
                    dane_form.append({"art": art_id, "ile": n})
        
        st.write("---")
        d_start = st.date_input("Start planu:", datetime.date.today())
        d_deadline = st.date_input("Termin (ogólny):", datetime.date.today() + datetime.timedelta(days=3))
        
        if st.form_submit_button("🚀 GENERUJ / DODAJ"):
            for poz in dane_form:
                st.session_state.kolejka.append({
                    "art": poz["art"], "ile": poz["ile"], 
                    "start": d_start, "termin": d_deadline
                })
            st.rerun()

    if st.button("🗑️ WYCZYŚĆ WSZYSTKO"):
        st.session_state.kolejka = []
        st.rerun()

# --- SZYBKIE OBLICZENIA ---
def przelicz_harmonogram(kolejka_
