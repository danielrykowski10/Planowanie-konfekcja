import streamlit as st
import datetime
import pandas as pd

# 1. Słownik tłumaczeń dni tygodnia
DNI_PL = {
    "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
    "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
}

# 2. Baza wydajności
WYDAJNOSC = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Turbo Planista", layout="wide")

# Inicjalizacja kolejki
if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- SZYBKA LOGIKA OBLICZENIOWA (Z CACHEM) ---
@st.cache_data
def generuj_harmonogram(kolejka_tuple):
    """
    Funkcja zbuforowana - liczy tylko gdy zmieni się treść kolejki.
    Używamy tuple, bo listy nie mogą być kluczem cache.
    """
    if not kolejka_tuple:
        return {}, []
    
    # Konwersja z powrotem na listę słowników do obliczeń
    zadania = [dict(z) for z in kolejka_tuple]
    zadania = sorted(zadania, key=lambda x: (x['start'], x['termin']))
    
    dni_planu = {}
    LIMIT_MINUT = 840  # 14h
    aktualna_data = min(z["start"] for z in zadania)
    wolny_czas = LIMIT_MINUT
    raport = []

    while zadania:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu:
            dzien_en = aktualna_data.strftime("%A")
            dni_planu[d_key] = {"data": aktualna_data, "dzien_pl": DNI_PL.get(dzien_en, dzien_en), "p": []}
        
        dostepne = [z for z in zadania if z["start"] <= aktualna_data]
        
        if not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = LIMIT_MINUT
            continue
            
        z = dostepne[0]
        wyd = WYDAJNOSC.get(z["art"], 70)
        ile_dzis = min(wolny_czas // wyd, z["ile"])
        
        if ile_dzis > 0:
            spoznienie = aktualna_data > z["termin"]
            wpis = {
                "Data": aktualna_data.strftime("%d.%m"),
                "Dzień": dni_planu[d_key]["dzien_pl"],
                "Artykuł": z["art"],
                "Palety": int(ile_dzis),
                "Termin": z["termin"].strftime("%d.%m"),
                "Opóźnienie": "TAK" if spoznienie else "NIE"
            }
            dni_planu[d_key]["p"].append(wpis)
            raport.append(wpis)
            z["ile"] -= ile_dzis
            wolny_czas -= (ile_dzis * wyd)
        
        if z["ile"] <= 0:
            zadania.remove(z)
            
        if wolny_czas < 52 or not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = LIMIT_MINUT
            
        if len(dni_planu) > 120: break # Bezpiecznik
        
    return dni_planu, raport

# --- OKNO DIALOGOWE ---
@st.dialog("➕ Dodaj Zamówienie")
def okno_dodawania():
    with st.container():
        cols = st.columns(2)
        nowe = []
        for i, art_id in enumerate(WYDAJNOSC.keys()):
            with cols[i % 2]:
                n = st.number_input(f"Art {art_id}", min_value=0, step=1, key=f"p_{art_id}")
                if n > 0: nowe.append({"art": art_id, "ile": n})
        
        st.divider()
        c1, c2 = st.columns(2)
        ds = c1.date_input("Start:", datetime.date.today())
        dt = c2.date_input("Termin:", datetime.date.today() + datetime.timedelta(days=2))
        
        if st.button("ZATWIERDŹ", use_container_width=True, type="primary"):
            for item in nowe:
