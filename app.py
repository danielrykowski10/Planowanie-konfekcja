import streamlit as st
import datetime
import pandas as pd

# 1. Baza wydajności (minuty na 1 paletę)
WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Produkcji", layout="wide")

# Inicjalizacja kolejki
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- FUNKCJA OKIENKA (DIALOG) ---
@st.dialog("📦 Dodaj Nowe Zamówienie")
def otworz_okno_zamowienia():
    st.write("Wpisz ilości palet dla artykułów:")
    
    with st.container():
        nowe_pozycje = []
        cols = st.columns(2)
        for i, (art_id, czas) in enumerate(WYDAJNOSC.items()):
            with cols[i % 2]:
                n = st.number_input(f"Art {art_id}", min_value=0, step=1, value=0)
                if n > 0:
                    nowe_pozycje.append({"art": art_id, "ile": n})
        
        st.write("---")
        d_start = st.date_input("Kiedy zacząć produkcję?", datetime.date.today())
        d_deadline = st.date_input("Termin dostawy (Deadline):", datetime.date.today() + datetime.timedelta(days=3))
        
        if st.button("ZATWIERDŹ I DODAJ DO PLANU", use_container_width=True):
            if nowe_pozycje:
                for p in nowe_po
