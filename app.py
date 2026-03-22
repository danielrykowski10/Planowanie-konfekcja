import streamlit as st
import datetime
import pandas as pd

# 1. Baza wydajności
wydajnosc = {
    "232": 70, "233": 60, "246": 70, "261": 84,
    "236": 84, "254": 52.5, "1221217": 120,
    "1221070": 52.5, "1221181": 84
}

st.set_page_config(page_title="Planista Mleczarnia", layout="wide")

st.title("🥛 Planista Produkcji - Panel Sterowania")

if 'kolejka' not in st.session_state:
    st.session_state.kolejka = []

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Importuj dane")
    plik = st.file_uploader("Wgraj Excel (art, ile, start, termin)", type=['xlsx', 'csv'])
    
    if plik:
        try:
            if plik.name.endswith('.csv'):
                df = pd.read_csv(plik)
            else:
                df = pd.read_excel(plik)
                
            if st.button("📥 Dodaj dane z pliku"):
                for _, row in df.iterrows():
                    st.session_state.kolejka.append({
                        "art": str(row['art']),
                        "ile": int(row['ile']),
                        "start": pd.to_datetime(row['start']).date(),
                        "termin": pd.to_datetime(row['termin']).date()
                    })
                st.success("Dodano!")
                st.rerun()
        except Exception as e:
            st.error(f"Błąd pliku: {e}")

    st.write("---")
    if st.button("🗑️ Wyczyść listę"):
        st.session_state.kolejka = []
        st.rerun()

# --- GŁÓWNY WIDOK ---
if not st.session_state.kolejka:
    st.info("Dodaj zamówienie przez plik lub powiedz mi, co dopisać.")
else:
    # Obliczenia (uproszczone)
    zadania = sorted([dict(z) for z in st.session_state.kolejka], key=lambda x: x['start'])
    dni_planu = {}
    aktualna_data = min(z["start"] for z in zadania)
    wolny_czas = 840 # 14h

    while zadania:
        d_key = aktualna_data.strftime("%Y-%m-%d")
        if d_key not in dni_planu:
            dni_planu[d_key] = {"data": aktualna_data, "pozycje": []}
        
        dostepne = [z for z in zadania if z["start"] <= aktualna_data]
        if not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            continue
            
        z = dostepne[0]
        wyd = wydajnosc.get(z["art"], 70)
        ile_dzis = min(wolny_czas // wyd, z["ile"])
        
        if ile_dzis > 0:
            dni_planu[d_key]["pozycje"].append({"art": z["art"], "ile": int(ile_dzis)})
            z["ile"] -= ile_dzis
            wolny_czas -= (ile_dzis * wyd)
        
        if z["ile"] <= 0:
            zadania.remove(z)
        
        if wolny_czas < 52 or not dostepne:
            aktualna_data += datetime.timedelta(days=1)
            wolny_czas = 840
        if len(dni_planu) > 100: break

    # Wyświetlanie
    cols = st.columns(5)
    for i, d_key in enumerate(sorted(dni_planu.keys())):
        d = dni_planu[d_key]
        with cols[i % 5]:
            st.markdown(f"### {d['data'].strftime('%d.%m')}")
            for p in d["pozycje"]:
                st.write(f"**{p['art']}**: {p['ile']} pal.")
