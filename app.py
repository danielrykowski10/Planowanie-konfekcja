import streamlit as st
import datetime
import pandas as pd
import json
import os

# --- KONFIGURACJA ZAPISU DANYCH ---
PLIK_DANYCH = "dane_zamowien.json"

def wczytaj_dane():
    if os.path.exists(PLIK_DANYCH):
        try:
            with open(PLIK_DANYCH, "r", encoding="utf-8") as f:
                dane = json.load(f)
                for z in dane:
                    z['termin'] = datetime.datetime.strptime(z['termin'], "%Y-%m-%d").date()
                return dane
        except Exception:
            return []
    return []

def zapisz_dane(kolejka):
    try:
        kolejka_do_zapisu = []
        for z in kolejka:
            z_kopia = z.copy()
            z_kopia['termin'] = z_kopia['termin'].strftime("%Y-%m-%d")
            kolejka_do_zapisu.append(z_kopia)
        with open(PLIK_DANYCH, "w", encoding="utf-8") as f:
            json.dump(kolejka_do_zapisu, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

WYDAJNOSC = {
    "232": 84, "233": 56, "236": 84, "261": 84,
    "246": 84, "254": 52.5, "1221217": 240,
    "1221070": 52.5, "1221181": 210
}

st.set_page_config(page_title="Konfekcja SM - Harmonogram", layout="wide")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = wczytaj_dane()

# --- LOGIKA PLANOWANIA ---
@st.cache_data
def generuj_plan_forward(kolejka_tuple, data_dzis):
    if not kolejka_tuple: 
        return {}, []

    zadania = [dict(z) for z in kolejka_tuple]
    plan_dni = {}
    raport = []
    MAX_CZAS_DOBA = 840 # 2 zmiany po 7h netto
    ostatni_art = None 

    while zadania:
        idx_wybranego = -1
